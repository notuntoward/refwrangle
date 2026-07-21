"""Regression tests for the Zotero → Obsidian note pipeline.

Run with:  uv run pytest test/test_regression.py -v
or:        python -m pytest test/test_regression.py -v

These tests cover the pure-Python logic that does NOT require a live Obsidian
instance, Zotero, or an actual vault on disk.  They are designed to catch
specific bugs that were introduced (and then fixed) during AI-assisted edits.
"""
from __future__ import annotations

import ast
import importlib
import json
import sys
import types
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Path setup: add the package directory so production modules are importable.
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
SRC = HERE.parent  # …/zmknote/
sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Helpers — stub out heavy side-effect imports before loading production code.
# ---------------------------------------------------------------------------

def _ensure_stubs():
    """Install lightweight stubs for packages that have unavoidable side-effects."""
    # flask
    if "flask" not in sys.modules:
        flask_mod = types.ModuleType("flask")
        flask_mod.Flask = MagicMock(return_value=MagicMock())
        flask_mod.jsonify = MagicMock(return_value=(MagicMock(), 200))
        flask_mod.request = MagicMock()
        sys.modules["flask"] = flask_mod

    # waitress
    if "waitress" not in sys.modules:
        waitress_mod = types.ModuleType("waitress")
        waitress_mod.serve = MagicMock()
        sys.modules["waitress"] = waitress_mod

    # tkinter + messagebox
    if "tkinter" not in sys.modules:
        tk_mod = types.ModuleType("tkinter")
        tk_mod.Tk = MagicMock
        tk_mod.Toplevel = MagicMock
        tk_mod.Label = MagicMock
        tk_mod.Frame = MagicMock
        tk_mod.Button = MagicMock
        tk_mod.LEFT = "left"
        sys.modules["tkinter"] = tk_mod
    if "tkinter.messagebox" not in sys.modules:
        mb_mod = types.ModuleType("tkinter.messagebox")
        mb_mod.showerror = MagicMock()
        mb_mod.showwarning = MagicMock()
        mb_mod.askyesno = MagicMock(return_value=True)
        sys.modules["tkinter.messagebox"] = mb_mod
        sys.modules["tkinter"].messagebox = mb_mod  # type: ignore[attr-defined]

    # bs4
    if "bs4" not in sys.modules:
        bs4_mod = types.ModuleType("bs4")
        bs4_mod.BeautifulSoup = MagicMock()
        element_mod = types.ModuleType("bs4.element")
        element_mod.Tag = MagicMock()
        bs4_mod.element = element_mod
        sys.modules["bs4"] = bs4_mod
        sys.modules["bs4.element"] = element_mod

# jinja2
    if "jinja2" not in sys.modules:
        jinja2_mod = types.ModuleType("jinja2")
        jinja2_mod.Environment = MagicMock
        jinja2_mod.Template = MagicMock
        sys.modules["jinja2"] = jinja2_mod


def _import_receiver():
    """Import the receiver module with all stubs in place."""
    _ensure_stubs()
    # open_obsidian_note must be the *real* module, not a stub
    if "open_obsidian_note" in sys.modules:
        del sys.modules["open_obsidian_note"]
    if "zotero_to_obsidian_note_receiver" in sys.modules:
        return sys.modules["zotero_to_obsidian_note_receiver"]
    return importlib.import_module("zotero_to_obsidian_note_receiver")


def _import_onu():
    """Import open_obsidian_note cleanly (no stubs needed for it)."""
    # Remove cached stub if any
    if "open_obsidian_note" in sys.modules:
        mod = sys.modules["open_obsidian_note"]
        # If it's the real module it will have check_obsidian_cli_available as a real fn
        if not isinstance(mod.check_obsidian_cli_available, MagicMock):
            return mod
        del sys.modules["open_obsidian_note"]
    return importlib.import_module("open_obsidian_note")


# ===========================================================================
# 1. validate_filepath (zotero_to_obsidian_note_receiver.py)
# ===========================================================================

class TestValidateFilepath:
    """Regression tests for validate_filepath().

    Bugs guarded against:
    - Returning valid=True for paths with Windows-invalid chars (e.g. ':')
    - Not catching reserved names (NUL, CON, COM1 …)
    - Accepting filenames with leading/trailing spaces
    - Treating the path separator '/' or '\\' in the *filename* as valid
    """

    @pytest.fixture(autouse=True)
    def _receiver(self):
        self.r = _import_receiver()

    def test_valid_normal_path(self):
        result = self.r.validate_filepath("lit/lit_notes/Smith2024.md")
        assert result["valid"] is True
        assert result["reason"] is None

    def test_empty_filepath(self):
        result = self.r.validate_filepath("")
        assert result["valid"] is False

    def test_none_filepath(self):
        result = self.r.validate_filepath(None)  # type: ignore[arg-type]
        assert result["valid"] is False

    @pytest.mark.parametrize("bad_char", ['<', '>', ':', '"', '|', '?', '*'])
    def test_windows_invalid_chars_in_filename(self, bad_char):
        result = self.r.validate_filepath(f"lit/lit_notes/Smith{bad_char}2024.md")
        assert result["valid"] is False, f"Expected invalid for char {bad_char!r}"

    @pytest.mark.parametrize("reserved", ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"])
    def test_windows_reserved_names(self, reserved):
        result = self.r.validate_filepath(f"lit/lit_notes/{reserved}.md")
        assert result["valid"] is False, f"Expected {reserved} to be invalid"

    def test_leading_space_in_filename(self):
        # " Smith2024.md" — leading space on the filename
        result = self.r.validate_filepath("lit/lit_notes/ Smith2024.md")
        assert result["valid"] is False

    def test_trailing_space_then_extension(self):
        # "Smith2024 .md" has a space before ".md"; the filename strip check
        # catches this because "Smith2024 .md".strip() != "Smith2024 .md" is False
        # (strip only removes whitespace at the ends of the string).
        # The actual trailing-space-before-extension case does NOT fire the current check,
        # so we document that this is NOT flagged (it passes as valid).
        result = self.r.validate_filepath("lit/lit_notes/Smith2024 .md")
        # Current implementation: a space before the extension is not flagged by the
        # leading/trailing-spaces check, so this will be valid=True.
        # If this ever changes the test should be updated.
        assert result["valid"] is True, (
            "Space-before-extension is currently NOT detected as invalid; "
            "update this test if behaviour changes"
        )

    def test_pure_trailing_space_in_filename(self):
        # "Smith2024 " (trailing space, no extension) — this IS caught
        result = self.r.validate_filepath("lit/lit_notes/Smith2024 ")
        assert result["valid"] is False

    def test_filename_ending_in_period(self):
        result = self.r.validate_filepath("lit/lit_notes/Smith2024.")
        assert result["valid"] is False

    def test_filename_too_long(self):
        long_name = "A" * 256  # 256 chars, exceeds 255 limit
        result = self.r.validate_filepath(f"lit/lit_notes/{long_name}.md")
        assert result["valid"] is False

    def test_valid_short_citekey(self):
        result = self.r.validate_filepath("lit/lit_notes/A.md")
        assert result["valid"] is True

    def test_valid_unicode_citekey(self):
        # Unicode characters are allowed (not Windows-forbidden)
        result = self.r.validate_filepath("lit/lit_notes/Müller2024.md")
        assert result["valid"] is True


# ===========================================================================
# 2. URI construction in open_obsidian_note (open_obsidian_note.py)
# ===========================================================================

class TestOpenObsidianNoteURI:
    """Regression tests for URI construction inside open_obsidian_note().

    Bugs guarded against:
    - filepath not percent-encoding '/' (must use safe='' for adv-uri filepath param)
    - Wrong URI scheme used for new-tab vs focus-existing-tab
    - Vault name not encoded in URI
    - cmd /c start was used (brittle), should use os.startfile on Windows
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        """Create a minimal fake vault with Advanced URI plugin installed+enabled."""
        self.vault = tmp_path / "My Vault"
        self.vault.mkdir()
        obsidian_dir = self.vault / ".obsidian"
        obsidian_dir.mkdir()
        # Enable community plugin
        plugins_dir = obsidian_dir / "plugins" / "obsidian-advanced-uri"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "data.json").write_text(
            '{"openFileWithoutWriteInNewPane": true}', encoding="utf-8"
        )
        (obsidian_dir / "community-plugins.json").write_text(
            '["obsidian-advanced-uri"]', encoding="utf-8"
        )
        # Create the note file so note_found=True
        note_dir = self.vault / "lit" / "lit_notes"
        note_dir.mkdir(parents=True)
        (note_dir / "Smith2024.md").touch()

        self.onu = _import_onu()

    # --- new_tab=True: should use adv-uri with newpane=true ---

    def _open(self, new_tab: bool):
        """Call open_obsidian_note with os.startfile patched out and CLI mocked as unavailable."""
        with patch("os.startfile"), \
             patch("open_obsidian_note.check_obsidian_cli_available") as mock_cli:
            # Make CLI appear unavailable so URI path is tested
            mock_cli.return_value = {"binary_on_path": False, "binary_responds": False, "cli_enabled": False, "obsidian_running": False, "failure_reason": "not_on_path"}
            return self.onu.open_obsidian_note(
                "lit/lit_notes/Smith2024.md",
                vault_path=self.vault,
                new_tab=new_tab,
            )

    def test_new_tab_uses_advanced_uri_with_newpane(self):
        status = self._open(new_tab=True)
        assert status["method_used"] == "advanced-uri-newtab"
        assert "newpane=true" in status["uri_used"]
        assert "adv-uri" in status["uri_used"]

    def test_new_tab_uri_contains_encoded_filepath(self):
        """Forward slashes in filepath must be %-encoded for adv-uri."""
        status = self._open(new_tab=True)
        uri = status["uri_used"]
        # The filepath parameter value must not contain literal '/'
        filepath_value = uri.split("filepath=")[1].split("&")[0]
        assert "/" not in filepath_value, (
            f"Unencoded '/' found in filepath value: {filepath_value!r}\n"
            f"Full URI: {uri}"
        )
        assert "%2F" in filepath_value, (
            f"Expected %2F encoding in filepath: {filepath_value!r}"
        )

    # --- new_tab=False: should use adv-uri WITHOUT newpane (focus mode) ---

    def test_focus_tab_uses_advanced_uri_without_newpane(self):
        status = self._open(new_tab=False)
        assert status["method_used"] == "advanced-uri-focus"
        assert "newpane" not in status["uri_used"], (
            "focus mode must NOT include newpane: " + status["uri_used"]
        )
        assert "adv-uri" in status["uri_used"]

    def test_focus_tab_uri_contains_encoded_filepath(self):
        """Forward slashes in filepath must be %-encoded even in focus mode."""
        status = self._open(new_tab=False)
        uri = status["uri_used"]
        filepath_value = uri.split("filepath=")[1].split("&")[0]
        assert "/" not in filepath_value, (
            f"Unencoded '/' found in filepath value in focus mode: {filepath_value!r}"
        )

    def test_vault_name_with_spaces_is_encoded(self):
        """Vault names containing spaces must be percent-encoded in the URI."""
        status = self._open(new_tab=True)
        vault_name = self.vault.name  # "My Vault"
        encoded = urllib.parse.quote(vault_name)  # "My%20Vault"
        assert encoded in status["uri_used"], (
            f"Encoded vault name {encoded!r} not found in URI: {status['uri_used']}"
        )
        assert " " not in status["uri_used"], "Unencoded space found in URI"

    # --- No plugin: fall back to standard obsidian:// ---

    def test_no_plugin_uses_standard_uri(self, tmp_path):
        vault_no_plugin = tmp_path / "Empty Vault"
        vault_no_plugin.mkdir()
        (vault_no_plugin / ".obsidian").mkdir()
        note_file = vault_no_plugin / "note.md"
        note_file.touch()

        with patch("os.startfile"), \
             patch("open_obsidian_note.check_obsidian_cli_available") as mock_cli:
            mock_cli.return_value = {"binary_on_path": False, "binary_responds": False, "cli_enabled": False, "obsidian_running": False, "failure_reason": "not_on_path"}
            status = self.onu.open_obsidian_note(
                "note.md",
                vault_path=vault_no_plugin,
                new_tab=True,
            )
        assert status["method_used"] == "standard"
        assert "obsidian://open" in status["uri_used"]
        assert "adv-uri" not in status["uri_used"]

    def test_windows_uses_os_startfile_not_cmd(self, tmp_path):
        """Regression: URI dispatch must use os.startfile, not cmd /c start."""
        import subprocess as sp

        dispatched_uris: list[str] = []

        def fake_startfile(uri):
            dispatched_uris.append(uri)

        with patch("os.startfile", side_effect=fake_startfile), \
             patch.object(sp, "run") as mock_run:
            self.onu.open_obsidian_note(
                "lit/lit_notes/Smith2024.md",
                vault_path=self.vault,
                new_tab=True,
            )

        # os.startfile must have been called
        assert len(dispatched_uris) == 1, "os.startfile should be called exactly once"
        # subprocess.run must NOT have been called for the URI dispatch
        # (it may be called internally by other parts, but not with 'cmd' or 'start')
        for c in mock_run.call_args_list:
            cmd_args = c[0][0] if c[0] else []
            assert "start" not in str(cmd_args) or "obsidian" in str(cmd_args), (
                f"subprocess.run called with cmd/start for URI dispatch: {cmd_args}"
            )


# ===========================================================================
# 2b. open_obsidian_note — prefer_uri skips the CLI entirely
# ===========================================================================

class TestPreferUriSkipsCli:
    """Regression tests for open_obsidian_note(prefer_uri=True).

    Bug guarded against:
    - prefer_uri=True was accepted as a caller-side intent but silently ignored
      by open_obsidian_note(), which always tried the CLI first when available.
      The raw CLI `open` command does not search existing tabs for the target
      file, so using it to "focus if already open" can produce a duplicate tab
      instead of focusing the existing one. prefer_uri=True must skip the CLI
      branch and go straight to the Advanced URI / standard URI method.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.vault = tmp_path / "My Vault"
        self.vault.mkdir()
        obsidian_dir = self.vault / ".obsidian"
        obsidian_dir.mkdir()
        plugins_dir = obsidian_dir / "plugins" / "obsidian-advanced-uri"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "data.json").write_text(
            '{"openFileWithoutWriteInNewPane": true}', encoding="utf-8"
        )
        (obsidian_dir / "community-plugins.json").write_text(
            '["obsidian-advanced-uri"]', encoding="utf-8"
        )
        note_dir = self.vault / "lit" / "lit_notes"
        note_dir.mkdir(parents=True)
        (note_dir / "Smith2024.md").touch()
        self.onu = _import_onu()

    def test_prefer_uri_never_calls_check_obsidian_cli_available(self):
        """When prefer_uri=True, the CLI availability check must not even run."""
        with patch("os.startfile"), \
             patch("open_obsidian_note.check_obsidian_cli_available") as mock_cli:
            self.onu.open_obsidian_note(
                "lit/lit_notes/Smith2024.md",
                vault_path=self.vault,
                new_tab=False,
                prefer_uri=True,
            )
        assert not mock_cli.called, "prefer_uri=True must skip check_obsidian_cli_available entirely"

    def test_prefer_uri_uses_advanced_uri_focus_even_when_cli_available(self):
        """Even if the CLI is fully available/responsive, prefer_uri=True must use the URI method."""
        with patch("os.startfile"), \
             patch("open_obsidian_note.check_obsidian_cli_available") as mock_cli, \
             patch("open_obsidian_note.open_note_via_cli") as mock_open_via_cli:
            mock_cli.return_value = {
                "binary_on_path": True, "binary_responds": True,
                "cli_enabled": True, "obsidian_running": True, "failure_reason": None,
            }
            status = self.onu.open_obsidian_note(
                "lit/lit_notes/Smith2024.md",
                vault_path=self.vault,
                new_tab=False,
                prefer_uri=True,
            )
        assert not mock_open_via_cli.called, "prefer_uri=True must not call open_note_via_cli"
        assert status["method_used"] == "advanced-uri-focus"
        assert status["uri_used"] != ""

    def test_without_prefer_uri_cli_is_used_when_available(self):
        """Sanity check: default behavior (prefer_uri=False) still tries CLI first."""
        with patch("open_obsidian_note.check_obsidian_cli_available") as mock_cli, \
             patch("open_obsidian_note.subprocess.run") as mock_run, \
             patch("open_obsidian_note.open_note_via_cli") as mock_open_via_cli:
            mock_cli.return_value = {
                "binary_on_path": True, "binary_responds": True,
                "cli_enabled": True, "obsidian_running": True, "failure_reason": None,
            }
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            mock_open_via_cli.return_value = {"success": True, "cli_output": "opened", "error": None}
            status = self.onu.open_obsidian_note(
                "lit/lit_notes/Smith2024.md",
                vault_path=self.vault,
                new_tab=False,
                prefer_uri=False,
            )
        assert mock_open_via_cli.called, "Default prefer_uri=False should still try CLI"
        assert status["method_used"] == "cli"


# ===========================================================================
# 3. check_obsidian_cli_available — Stage 3 broad except coverage
# ===========================================================================

class TestCliAvailability:
    """Regression tests for check_obsidian_cli_available().

    Bugs guarded against:
    - Stage 3 unexpected exception leaving cli_enabled=None instead of False
    - Incorrect failure_reason values
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.vault = tmp_path / "Vault"
        self.vault.mkdir()
        self.onu = _import_onu()

    def test_cli_not_on_path_returns_not_on_path(self):
        with patch("open_obsidian_note.shutil.which", return_value=None):
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["binary_on_path"] is False
        assert result["failure_reason"] == "not_on_path"
        # cli_enabled starts as None and is never set (returned early)
        assert result["cli_enabled"] is None

    def test_version_fails_but_status_succeeds_still_enabled(self):
        """Obsidian 1.12.x may return non-zero for `obsidian version` even though the CLI works."""
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="unknown command"),  # version
                MagicMock(returncode=0, stdout="ok", stderr=""),                # status
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["binary_responds"] is True
        assert result["cli_enabled"] is True
        assert result["failure_reason"] is None

    def test_version_fails_and_status_reports_not_running(self):
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="unknown command"),  # version
                MagicMock(returncode=1, stdout="", stderr="obsidian not running"),  # status
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["binary_responds"] is True
        assert result["cli_enabled"] is False
        assert result["failure_reason"] == "obsidian_not_running"

    def test_version_fails_and_status_fails_disabled(self):
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="unknown command"),  # version
                MagicMock(returncode=1, stdout="", stderr="command line interface disabled"),  # status
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["binary_responds"] is True
        assert result["cli_enabled"] is False
        assert result["failure_reason"] == "cli_disabled"

    def test_version_fails_and_status_raises_returns_binary_broken(self):
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="unknown command"),  # version
                OSError("broken pipe"),  # status — unexpected
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["binary_responds"] is False
        assert result["cli_enabled"] is False
        assert result["failure_reason"] == "binary_broken"

    def test_stage3_timeout_sets_cli_enabled_false(self):
        import subprocess as sp
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="1.0", stderr=""),       # version call
                sp.TimeoutExpired(cmd="obsidian", timeout=10),           # status call
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["cli_enabled"] is False
        assert result["failure_reason"] == "obsidian_not_running"

    def test_stage3_unexpected_exception_sets_cli_enabled_false(self):
        """Regression: OSError in Stage 3 previously left cli_enabled=None."""
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="1.0", stderr=""),  # version
                OSError("permission denied"),                       # status — unexpected
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["cli_enabled"] is False, (
            "cli_enabled must be False (not None) when Stage 3 raises unexpected exception"
        )
        assert result["failure_reason"] is not None

    def test_all_stages_pass_returns_cli_enabled_true(self):
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="1.0", stderr=""),  # version
                MagicMock(returncode=0, stdout="ok", stderr=""),   # status
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["cli_enabled"] is True
        assert result["failure_reason"] is None

    def test_obsidian_not_running_detected_from_stderr(self):
        with patch("open_obsidian_note.shutil.which", return_value="/usr/bin/obsidian"), \
             patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="1.0", stderr=""),
                MagicMock(returncode=1, stdout="", stderr="obsidian not running"),
            ]
            result = self.onu.check_obsidian_cli_available(self.vault)
        assert result["cli_enabled"] is False
        assert result["failure_reason"] == "obsidian_not_running"


# ===========================================================================
# 3b. is_note_open_in_obsidian — workspace file parsing
# ===========================================================================

class TestIsNoteOpenInObsidian:
    """Tests for is_note_open_in_obsidian()."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.vault = tmp_path / "Vault"
        self.vault.mkdir()
        self.obsidian_dir = self.vault / ".obsidian"
        self.obsidian_dir.mkdir()
        self.onu = _import_onu()

    def _write_workspace(self, data: dict) -> None:
        workspace_file = self.obsidian_dir / "workspace.json"
        with workspace_file.open("w", encoding="utf-8") as f:
            json.dump(data, f)

    def _workspace_with_file(self, file_path: str) -> dict:
        return {
            "workspace": {
                "left": {
                    "type": "split",
                    "children": [
                        {
                            "type": "leaf",
                            "state": {
                                "type": "markdown",
                                "state": {
                                    "file": file_path,
                                    "mode": "source",
                                },
                            },
                        }
                    ],
                }
            }
        }

    def test_note_open_in_leaf_returns_true(self):
        self._write_workspace(
            self._workspace_with_file("lit/lit_notes/Studio25mostEfficientTraveler.md")
        )
        result = self.onu.is_note_open_in_obsidian(
            "lit/lit_notes/Studio25mostEfficientTraveler.md", self.vault
        )
        assert result is True

    def test_note_not_open_returns_false(self):
        self._write_workspace(
            self._workspace_with_file("lit/lit_notes/OtherNote.md")
        )
        result = self.onu.is_note_open_in_obsidian(
            "lit/lit_notes/Studio25mostEfficientTraveler.md", self.vault
        )
        assert result is False

    def test_missing_workspace_file_returns_false(self):
        result = self.onu.is_note_open_in_obsidian(
            "lit/lit_notes/Studio25mostEfficientTraveler.md", self.vault
        )
        assert result is False

    def test_malformed_workspace_file_returns_false(self):
        workspace_file = self.obsidian_dir / "workspace.json"
        workspace_file.write_text("not valid json", encoding="utf-8")
        result = self.onu.is_note_open_in_obsidian(
            "lit/lit_notes/Studio25mostEfficientTraveler.md", self.vault
        )
        assert result is False

    def test_normalizes_backslashes(self):
        self._write_workspace(
            self._workspace_with_file("lit/lit_notes/Studio25mostEfficientTraveler.md")
        )
        result = self.onu.is_note_open_in_obsidian(
            "lit\\lit_notes\\Studio25mostEfficientTraveler.md", self.vault
        )
        assert result is True


# ===========================================================================
# 4. open_note_via_cli — new_tab parameter
# ===========================================================================

class TestOpenNoteViaCli:
    """Regression tests for open_note_via_cli().

    Bugs guarded against:
    - new_tab=True not appending 'newtab' to CLI command
    - new_tab=False incorrectly appending 'newtab'
    - Errors not propagated in result dict
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.vault = tmp_path / "Vault"
        self.vault.mkdir()
        self.onu = _import_onu()

    def test_new_tab_true_includes_newtab_arg(self):
        with patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            self.onu.open_note_via_cli("lit/note.md", self.vault, new_tab=True)
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "newtab" in cmd, f"'newtab' missing from CLI command: {cmd}"

    def test_new_tab_false_excludes_newtab_arg(self):
        with patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            self.onu.open_note_via_cli("lit/note.md", self.vault, new_tab=False)
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "newtab" not in cmd, f"'newtab' should be absent from CLI command: {cmd}"

    def test_new_tab_default_is_true(self):
        with patch("open_obsidian_note.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            self.onu.open_note_via_cli("lit/note.md", self.vault)
        cmd = mock_run.call_args[0][0]
        assert "newtab" in cmd, "Default new_tab=True should include 'newtab'"

    def test_timeout_returns_error_dict(self):
        import subprocess as sp
        with patch("open_obsidian_note.subprocess.run",
                   side_effect=sp.TimeoutExpired(cmd="obsidian", timeout=10)), \
             patch("open_obsidian_note.time.sleep"):
            result = self.onu.open_note_via_cli("lit/note.md", self.vault, timeout=0.5, interval=0.1)
        assert result["success"] is False
        assert result["error"] is not None

    def test_non_zero_return_code_returns_error(self):
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            cmd_str = " ".join(cmd)
            if "status" in cmd:
                return MagicMock(returncode=0, stdout="ok", stderr="")
            elif "open" in cmd and "path=" in cmd_str:
                return MagicMock(returncode=1, stdout="", stderr="not found")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        with patch("open_obsidian_note.subprocess.run", side_effect=mock_run_side_effect), \
             patch("open_obsidian_note.time.sleep"):
            result = self.onu.open_note_via_cli("lit/note.md", self.vault, timeout=0.5, interval=0.1)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_success_returns_success_dict(self):
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            cmd_str = " ".join(cmd)
            if "status" in cmd:
                return MagicMock(returncode=0, stdout="ok", stderr="")
            elif "open" in cmd and "path=" in cmd_str:
                return MagicMock(returncode=0, stdout="opened", stderr="")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        with patch("open_obsidian_note.subprocess.run", side_effect=mock_run_side_effect), \
             patch("open_obsidian_note.time.sleep"):
            result = self.onu.open_note_via_cli("lit/note.md", self.vault, timeout=0.5, interval=0.1)
        assert result["success"] is True
        assert result["error"] is None

    # --- Vault not open: wait for vault to be ready before opening note ---

    def test_waits_for_vault_ready_before_opening_note(self):
        """When vault is not open, should poll status until vault is ready before opening note."""
        call_count = {"status": 0, "open": 0}
        
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            cmd_str = " ".join(cmd)
            if "open" in cmd and "path=" in cmd_str:
                call_count["open"] += 1
                return MagicMock(returncode=0, stdout="opened", stderr="")
            elif "status" in cmd:
                call_count["status"] += 1
                # First TWO status checks fail (initial + first poll), third succeeds
                if call_count["status"] <= 2:
                    return MagicMock(returncode=1, stdout="", stderr="not running")
                return MagicMock(returncode=0, stdout="ok", stderr="")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        with patch("open_obsidian_note.subprocess.run", side_effect=mock_run_side_effect), \
             patch("open_obsidian_note.time.sleep"):
            result = self.onu.open_note_via_cli("lit/note.md", self.vault, timeout=10, interval=0.1)
        
        assert result["success"] is True
        assert call_count["status"] >= 3, "Should have polled status until vault ready"
        assert call_count["open"] == 1, "Open should be called exactly once after vault ready"

    def test_returns_failure_if_vault_never_becomes_ready(self):
        """When vault fails to open within timeout, should return failure."""
        def mock_run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "status" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="not running")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")
        
        with patch("open_obsidian_note.subprocess.run", side_effect=mock_run_side_effect), \
             patch("open_obsidian_note.time.sleep"):
            result = self.onu.open_note_via_cli("lit/note.md", self.vault, timeout=0.5, interval=0.1)
        
        assert result["success"] is False
        assert "Timed out waiting for vault" in result["error"]


# ===========================================================================
# 5. ask_overwrite_popup return values
# ===========================================================================

class TestAskOverwritePopup:
    """Regression tests for ask_overwrite_popup().

    Bugs guarded against:
    - Returning 'open' (dead value that was removed in the refactor)
    - Returning something other than 'overwrite', 'skip', or 'skip_all'
    """

    @pytest.fixture(autouse=True)
    def _receiver(self):
        self.r = _import_receiver()

    def test_single_item_yes_returns_overwrite(self):
        with patch.object(self.r.tk, "Tk"), \
             patch.object(self.r.messagebox, "askyesno", return_value=True):
            result = self.r.ask_overwrite_popup(
                "Smith2024", is_last_item=True, total_items=1, request_id="x"
            )
        assert result == "overwrite"

    def test_single_item_no_returns_skip(self):
        with patch.object(self.r.tk, "Tk"), \
             patch.object(self.r.messagebox, "askyesno", return_value=False):
            result = self.r.ask_overwrite_popup(
                "Smith2024", is_last_item=True, total_items=1, request_id="x"
            )
        assert result == "skip"

    def test_result_is_never_open(self):
        """Regression: 'open' was once a return value; must never be returned."""
        with patch.object(self.r.tk, "Tk"), \
             patch.object(self.r.messagebox, "askyesno", return_value=True):
            result = self.r.ask_overwrite_popup(
                "Smith2024", is_last_item=True, total_items=1, request_id="x"
            )
        assert result != "open", "ask_overwrite_popup must never return 'open'"

    def test_all_valid_return_values_are_in_allowed_set(self):
        valid_values = {"overwrite", "skip", "skip_all"}
        for yes_no in [True, False]:
            with patch.object(self.r.tk, "Tk"), \
                 patch.object(self.r.messagebox, "askyesno", return_value=yes_no):
                result = self.r.ask_overwrite_popup(
                    "Smith2024", is_last_item=True, total_items=1, request_id="x"
                )
            assert result in valid_values, f"Unexpected return value: {result!r}"


# ===========================================================================
# 6. Startup server does not block while CLI check is in progress
# ===========================================================================

class TestStartupCliCheckNonBlocking:
    """Regression: startup CLI check must be non-blocking.

    Bug: check_obsidian_cli_available takes up to 15 s; if called synchronously
    before serve() it causes early webhook requests to fail with 'connection refused'.
    Fix: run the check in a daemon thread so serve() starts immediately.
    """

    def test_background_cli_check_is_a_thread(self):
        """The startup block must spawn a Thread, not call check_obsidian_cli_available directly."""
        module_path = SRC / "zotero_to_obsidian_note_receiver.py"
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find the `if __name__ == "__main__":` block
        main_block_body: list = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (isinstance(test, ast.Compare)
                        and isinstance(test.left, ast.Name)
                        and test.left.id == "__name__"
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"):
                    main_block_body = node.body
                    break

        assert main_block_body, "Could not locate if __name__ == '__main__' block"

        # Search for threading.Thread(...).start() within the main block
        found_thread_start = False
        wrapper = ast.Module(body=main_block_body, type_ignores=[])
        for node in ast.walk(wrapper):
            if isinstance(node, ast.Call):
                src_segment = ast.unparse(node)
                if "Thread" in src_segment and ".start()" in src_segment:
                    found_thread_start = True
                    break

        assert found_thread_start, (
            "startup block must call threading.Thread(...).start() for the CLI check. "
            "serve() must never be delayed by the CLI subprocess calls."
        )

    def test_serve_call_is_after_thread_start(self):
        """serve() must appear AFTER the Thread.start() call in the main block."""
        module_path = SRC / "zotero_to_obsidian_note_receiver.py"
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        main_block_body: list = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (isinstance(test, ast.Compare)
                        and isinstance(test.left, ast.Name)
                        and test.left.id == "__name__"
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"):
                    main_block_body = node.body
                    break

        # Collect line numbers of Thread.start() and serve() calls
        thread_start_lines = []
        serve_lines = []
        for node in ast.walk(ast.Module(body=main_block_body, type_ignores=[])):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                src = ast.unparse(node.value)
                if "Thread" in src and ".start()" in src:
                    thread_start_lines.append(node.lineno)
                if src.startswith("serve("):
                    serve_lines.append(node.lineno)

        assert thread_start_lines, "No Thread.start() found in __main__ block"
        assert serve_lines, "No serve() call found in __main__ block"
        assert min(serve_lines) > min(thread_start_lines), (
            f"serve() (line {min(serve_lines)}) must appear after Thread.start() "
            f"(line {min(thread_start_lines)})"
        )


# ===========================================================================
# 7. Callout builders + template rendering for the Zotero literature note.
#
# These tests guard against the bug where the [!info] callout's title line
# was concatenated with the "Abstract" / "Author" lines (because Jinja
# trim_blocks stripped the newline between them), causing "Abstract" to show
# up in the folded callout title instead of inside the hidden body.
#
# They also guard the [!note] callout where Zotero note content used to
# leak outside the callout because {%- for note in notes -%} ate the
# surrounding newlines and the broken `note.tags` reference would crash.
# ===========================================================================

def _import_receiver_with_real_jinja():
    """Import the receiver module with the real jinja2 available.

    The default `_import_receiver()` helper installs a MagicMock `jinja2`
    stub so the module can be imported without the real dependency. For
    template-rendering tests we need jinja2 to actually parse, render, and
    apply trim_blocks/lstrip_blocks — so we install stubs for every other
    heavy side-effect (flask, waitress, tkinter, bs4) but leave the real
    jinja2 in place.
    """
    import importlib

    # Drop any stubbed modules so we can install fresh, minimal stubs.
    for name in (
        "flask", "waitress", "tkinter", "tkinter.messagebox",
        "bs4", "bs4.element",
        "zotero_to_obsidian_note_receiver", "open_obsidian_note",
    ):
        sys.modules.pop(name, None)

    _ensure_stubs()

    # Re-stub bs4 as a MagicMock (the _ensure_stubs default stubs bs4).
    # We need the *real* jinja2 to be importable, so make sure it's not
    # replaced with a MagicMock stub.
    sys.modules.pop("jinja2", None)
    import jinja2 as _real_jinja2  # noqa: F401  (real package import)

    # open_obsidian_note must be the *real* module.
    import open_obsidian_note  # noqa: F401
    return importlib.import_module("zotero_to_obsidian_note_receiver")


class TestCalloutBuilders:
    """Unit tests for the pure-Python callout builder helpers.

    These functions were added when the Jinja template stopped building the
    [!info] callout title/body inline, to keep callout whitespace safe from
    trim_blocks / lstrip_blocks collapse bugs.
    """

    @pytest.fixture(autouse=True)
    def _receiver(self):
        self.r = _import_receiver_with_real_jinja()

    # --- creator_display_name -------------------------------------------------

    def test_creator_uses_name_field_when_present(self):
        assert self.r.creator_display_name(
            {"creatorType": "author", "name": "Some Institution"}
        ) == "Some Institution"

    def test_creator_combines_last_and_first(self):
        assert self.r.creator_display_name(
            {"creatorType": "author", "lastName": "Rowland", "firstName": "Christopher"}
        ) == "Rowland, Christopher"

    def test_creator_handles_missing_first_name(self):
        assert self.r.creator_display_name(
            {"creatorType": "editor", "lastName": "Smith"}
        ) == "Smith"

    def test_creator_handles_missing_last_name(self):
        assert self.r.creator_display_name(
            {"creatorType": "editor", "firstName": "Bob"}
        ) == "Bob"

    def test_creator_handles_empty_fields(self):
        assert self.r.creator_display_name(
            {"creatorType": "editor", "lastName": "", "firstName": ""}
        ) == ""

    # --- build_info_callout_links --------------------------------------------

    def test_links_only_contains_zotero_when_nothing_else(self):
        out = self.r.build_info_callout_links(
            {"desktopURI": "zotero://select/library/items/X", "DOI": "", "url": "", "attachments": []}
        )
        assert out == "[**Zotero**](zotero://select/library/items/X)"

    def test_links_includes_doi_when_present(self):
        out = self.r.build_info_callout_links(
            {"desktopURI": "zotero://x", "DOI": "10.1234/abc", "url": "", "attachments": []}
        )
        assert "[**DOI**](https://doi.org/10.1234/abc)" in out

    def test_links_includes_url_when_present(self):
        out = self.r.build_info_callout_links(
            {"desktopURI": "zotero://x", "DOI": "", "url": "https://example.com", "attachments": []}
        )
        assert "[**URL**](https://example.com)" in out

    def test_links_joins_with_pipe_separator(self):
        out = self.r.build_info_callout_links(
            {"desktopURI": "zotero://x", "DOI": "10.1/x", "url": "https://e.com", "attachments": []}
        )
        assert out.count(" | ") == 2  # Zotero | DOI | URL

    @pytest.mark.parametrize("suffix,label", [
        (".pdf", "PDF"), (".html", "HTM"), (".docx", "DOC"),
        (".pptx", "PPT"), (".epub", "EPUB"), (".txt", "TXT"),
    ])
    def test_links_includes_attachment_for_known_suffix(self, suffix, label):
        item = {
            "desktopURI": "zotero://x", "DOI": "", "url": "",
            "attachments": [{"path": f"MyPaper{suffix}"}],
        }
        out = self.r.build_info_callout_links(item)
        assert f"[[MyPaper{suffix}|{label}]]" in out, f"Missing {label} link in: {out!r}"

    def test_links_ignores_unknown_attachment_suffix(self):
        item = {
            "desktopURI": "zotero://x", "DOI": "", "url": "",
            "attachments": [{"path": "MyPaper.xyz"}],
        }
        out = self.r.build_info_callout_links(item)
        assert "xyz" not in out
        assert "MyPaper" not in out

    def test_links_handles_attachment_with_object_attrs(self):
        """Attachments can arrive as dicts or objects; both must work."""
        class Att:
            path = "Foo.html"
        item = {
            "desktopURI": "zotero://x", "DOI": "", "url": "", "attachments": [Att()],
        }
        out = self.r.build_info_callout_links(item)
        assert "[[Foo.html|HTM]]" in out

    def test_links_basename_strips_windows_separators(self):
        item = {
            "desktopURI": "zotero://x", "DOI": "", "url": "",
            "attachments": [{"path": "C:\\foo\\bar.html"}],
        }
        out = self.r.build_info_callout_links(item)
        assert "[[bar.html|HTM]]" in out
        # No backslash or forward slash from the path inside the link
        assert "[[bar.html|HTM]]**" in out

    # --- build_info_callout_prefix -------------------------------------------

    def test_prefix_empty_when_no_abstract_no_creators(self):
        out = self.r.build_info_callout_prefix({"abstractNote": "", "creators": []})
        assert out == ""

    def test_prefix_empty_when_abstract_whitespace_only(self):
        out = self.r.build_info_callout_prefix({"abstractNote": "   \n  ", "creators": []})
        assert out == ""

    def test_prefix_contains_abstract_block(self):
        out = self.r.build_info_callout_prefix({"abstractNote": "An abstract.", "creators": []})
        # Must include the Abstract label and the abstract text, each on a
        # quoted line, with bare-quoted spacer lines around them.
        assert "> **Abstract**" in out
        assert "> An abstract." in out
        # Spacer quoted-blank lines around the block
        assert out.startswith(">\n")
        assert out.endswith(">\n")

    def test_prefix_groups_creators_by_type(self):
        item = {"abstractNote": "", "creators": [
            {"creatorType": "author", "lastName": "Smith", "firstName": "A"},
            {"creatorType": "author", "lastName": "Jones", "firstName": "B"},
            {"creatorType": "editor", "lastName": "Ed", "firstName": None},
        ]}
        out = self.r.build_info_callout_prefix(item)
        assert "> **Author**:: Smith, A, Jones, B" in out
        assert "> **Editor**:: Ed" in out

    def test_prefix_strips_embedded_newlines_from_abstract(self):
        out = self.r.build_info_callout_prefix({
            "abstractNote": "Line 1.\nLine 2.\nLine 3.", "creators": [],
        })
        # Newlines in the abstract must be replaced with spaces so they
        # don't break the callout body.
        assert "Line 1. Line 2. Line 3." in out
        assert "\nLine 2." not in out  # no unquoted continuation lines

    def test_prefix_combines_abstract_then_creators_with_separator(self):
        out = self.r.build_info_callout_prefix({
            "abstractNote": "An abstract.",
            "creators": [{"creatorType": "author", "lastName": "Smith", "firstName": "A"}],
        })
        # Abstract block first, then a quoted blank, then the creator block,
        # then a trailing quoted blank.
        assert "> **Abstract**" in out
        assert "> An abstract." in out
        assert "> **Author**:: Smith, A" in out
        # Abstract section must come before the author section
        assert out.index("> **Abstract**") < out.index("> **Author**")


class TestCalloutTemplateRendering:
    """Render the real template and assert the markdown is correctly quoted.

    These are the regressions that motivated moving callout construction out
    of Jinja. They would have failed against the previous template.
    """

    @pytest.fixture(autouse=True)
    def _receiver(self):
        self.r = _import_receiver_with_real_jinja()

    def _render(self, **overrides):
        """Render the template with a minimal valid item context."""
        import jinja2 as real_jinja2
        env = real_jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        env.filters["yaml_escape"] = self.r.yaml_escape
        template = env.from_string(self.r.template_str)
        item = dict(
            title="A test title",
            citekey="test24",
            tags=[],
            collections=[],
            exportDate="2024-01-01",
            desktopURI="zotero://select/library/items/X",
            DOI="",
            url="",
            attachments=[],
            abstractNote="",
            creators=[],
            date="2024",
            itemkey="X",
            itemType="book",
            publicationTitle="",
            volume="",
            issue="",
            publisher="",
            place="",
            pages="",
            ISBN="",
            allTags=[],
            relations=[],
            bibliography="",
            notes=[],
        )
        item.update(overrides)
        # Build the prefix/links exactly the way write_obsidian_md_note does.
        item["infoCalloutLinks"] = self.r.build_info_callout_links(item)
        item["infoCalloutPrefix"] = self.r.build_info_callout_prefix(item)
        return template.render(**item)

    def _info_callout_block(self, rendered):
        """Extract the [!info] callout lines from rendered markdown."""
        lines = rendered.splitlines()
        start = next(i for i, ln in enumerate(lines) if "[!info]-" in ln)
        end = next(
            i for i in range(start + 1, len(lines))
            if lines[i].strip() == "" and (i + 1 >= len(lines) or not lines[i + 1].startswith(">"))
        )
        return lines[start:end]

    # --- [!info] title line ---------------------------------------------------

    def test_info_title_line_is_a_single_line(self):
        """The [!info] title must be a single line; no Abstract/Author bleed-in."""
        out = self._render(abstractNote="Abstract body here.")
        info = self._info_callout_block(out)
        title_line = next(ln for ln in info if ln.startswith("> [!info]-"))
        # Must NOT contain Abstract label
        assert "Abstract" not in title_line, (
            f"Abstract leaked into title line: {title_line!r}"
        )
        # Must NOT contain Author label
        assert "**Author**" not in title_line

    def test_info_title_line_does_not_end_with_quote_marker(self):
        """The title line must not end with a stray '>' that would merge
        with the next body line if a renderer is line-blind."""
        out = self._render(abstractNote="Abstract body here.")
        info = self._info_callout_block(out)
        title_line = next(ln for ln in info if ln.startswith("> [!info]-"))
        assert not title_line.rstrip().endswith(">"), (
            f"Title line ends with '>': {title_line!r}"
        )

    def test_info_title_does_not_have_double_blockquote_marker(self):
        """No '>>' anywhere on the title line (the old '>> **Abstract**' bug)."""
        out = self._render(
            abstractNote="Abstract body here.",
            creators=[{"creatorType": "author", "lastName": "S", "firstName": "A"}],
        )
        info = self._info_callout_block(out)
        title_line = next(ln for ln in info if ln.startswith("> [!info]-"))
        assert ">>" not in title_line, f"Double blockquote in title: {title_line!r}"

    def test_info_body_lines_are_quoted_until_metadata_starts(self):
        """Every line between the title and the metadata block must start with '> '."""
        out = self._render(abstractNote="Abstract body here.")
        info = self._info_callout_block(out)
        for line in info:
            assert line.startswith(">"), (
                f"Unquoted line inside callout: {line!r}"
            )

    # --- abstract body --------------------------------------------------------

    def test_abstract_appears_on_its_own_quoted_line(self):
        out = self._render(abstractNote="The abstract content.")
        info = self._info_callout_block(out)
        assert "> **Abstract**" in info
        assert "> The abstract content." in info

    def test_abstract_is_separate_line_from_title(self):
        """Regression: previously Abstract was concatenated onto the title line."""
        out = self._render(abstractNote="The abstract content.")
        info = self._info_callout_block(out)
        title_idx = next(i for i, ln in enumerate(info) if "[!info]-" in ln)
        abstract_idx = info.index("> **Abstract**")
        assert abstract_idx > title_idx
        assert abstract_idx == title_idx + 2, (
            f"Abstract must be exactly 2 lines after title (with blank quoted line); "
            f"got indices {title_idx} -> {abstract_idx}"
        )

    # --- creator body ---------------------------------------------------------

    def test_creator_appears_on_its_own_quoted_line(self):
        out = self._render(
            creators=[{"creatorType": "author", "lastName": "Smith", "firstName": "A"}]
        )
        info = self._info_callout_block(out)
        assert any("**Author**:: Smith, A" in ln for ln in info)

    def test_creator_not_concatenated_with_metadata(self):
        """Regression: Author used to get joined with the Title metadata line."""
        out = self._render(
            creators=[{"creatorType": "author", "lastName": "Smith", "firstName": "A"}]
        )
        for line in out.splitlines():
            assert ":: Smith, A> **Title**" not in line, (
                f"Creator concatenated with metadata: {line!r}"
            )

    # --- no abstract / no creator (minimal item) ------------------------------

    def test_no_abstract_no_creators_still_properly_quoted(self):
        out = self._render()
        info = self._info_callout_block(out)
        title_idx = next(i for i, ln in enumerate(info) if "[!info]-" in ln)
        # The next line in the callout should be the Title metadata line
        # (no unquoted blank line in between).
        assert info[title_idx + 1] == "> **Title**:: \"A test title\"", (
            f"Expected Title on line right after title; got: {info[title_idx + 1]!r}"
        )

    # --- attachment links in title -------------------------------------------

    def test_attachment_html_link_is_in_title(self):
        out = self._render(attachments=[{"path": "MyPaper.html"}])
        info = self._info_callout_block(out)
        title_line = next(ln for ln in info if "[!info]-" in ln)
        assert "[[MyPaper.html|HTM]]" in title_line

    # --- notes callout --------------------------------------------------------

    def test_notes_callout_title_does_not_include_note_text(self):
        out = self._render(notes=["Some note content.\nLine two."])
        # The [!note] title line should be clean
        lines = out.splitlines()
        note_title_idx = next(i for i, ln in enumerate(lines) if "[!note]-" in ln)
        title_line = lines[note_title_idx]
        assert "Some note content" not in title_line
        assert "Line two" not in title_line

    def test_notes_callout_body_lines_are_quoted(self):
        out = self._render(notes=["Some note content.\nLine two.", "Second note."])
        lines = out.splitlines()
        note_title_idx = next(i for i, ln in enumerate(lines) if "[!note]-" in ln)
        # Collect consecutive lines starting with '>' after the title
        body = []
        for ln in lines[note_title_idx + 1:]:
            if not ln.startswith(">"):
                break
            body.append(ln)
        assert "> Some note content." in body
        assert "> Line two." in body
        assert "> Second note." in body

    def test_notes_callout_no_external_horizontal_rule_after_title(self):
        """A bare '---' after the [!note] title would close the callout and
        render as a horizontal rule. Verify the line right after the title
        is a quoted blank, not an unquoted '---'."""
        out = self._render(notes=["Some note."])
        lines = out.splitlines()
        note_title_idx = next(i for i, ln in enumerate(lines) if "[!note]-" in ln)
        # Next line should be ">", not "---"
        assert lines[note_title_idx + 1] == ">", (
            f"Expected '>' after notes title, got: {lines[note_title_idx + 1]!r}"
        )
