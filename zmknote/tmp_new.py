def zotero_note_html_to_md(html_content: str, remove_first_div: bool = False):
    """
    Convert Zotero note HTML content to Obsidian-compatible markdown
    
    Args:
        html_content: The HTML content to convert
        remove_first_div: If True, removes the first div section if it exists
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove the first div if requested and if it exists
    if remove_first_div:
        first_div = soup.find('div')
        if first_div:
            first_div.extract()  # Removes the element from the tree
    
    # Process citations with correct Zotero URI format
    for citation in soup.find_all('span', class_='citation'):
        citation_item = citation.find('span', class_='citation-item')
        if citation_item and citation.get('data-citation'):
            try:
                citation_data = unquote(citation['data-citation'])
                citation_json = json.loads(citation_data, strict=False)
                
                if citation_json.get('citationItems') and citation_json['citationItems'][0].get('uris'):
                    raw_uri = citation_json['citationItems'][0]['uris'][0]
                    item_id = raw_uri.split('/')[-1]
                    zotero_uri = f"zotero://select/library/items/{item_id}"
                    citation.replace_with(f"[{citation_item.text}]({zotero_uri})")
            except Exception as e:
                print(f"Citation parsing error: {e}")
                citation.replace_with(citation_item.text)
    
    # Process formatting tags
    for tag in soup.find_all(['b', 'strong']):
        tag.replace_with(f"**{tag.get_text()}**")
    
    for tag in soup.find_all(['i', 'em']):
        tag.replace_with(f"*{tag.get_text()}*")
    
    for span in soup.find_all('span'):
        if span.get('style') and 'background-color' in span.get('style'):
            span.replace_with(f"=={span.get_text()}==")
    
    # Build markdown document
    md_lines = []
    
    # Process each type of element in order of appearance
    for element in soup.body.children if soup.body else soup.children:
        if element.name:
            if element.name.startswith('h'):
                level = int(element.name[1])
                md_lines.append(f"{'#' * level} {element.get_text().strip()}")
            elif element.name in ['ul', 'ol']:
                list_lines = process_list(element, is_root=True)
                md_lines.extend(list_lines)
            elif element.name == 'blockquote':
                quote_lines = element.get_text().strip().split('\n')
                md_lines.append('\n'.join([f"> {line.strip()}" for line in quote_lines]))
            elif element.name == 'p' and element.get_text().strip():
                md_lines.append(element.get_text().strip())
    
    # Add proper spacing
    result_lines = [""]  # Start with a blank line at the top
    
    # Helper function to check if a line is a paragraph (not a list item, header, or blockquote)
    def is_paragraph(line):
        return line.strip() and not line.strip().startswith(('- ', '#', '>'))
    
    # Process each line
    for i, line in enumerate(md_lines):
        # Add the current line
        result_lines.append(line)
        
        # If current line and next line are both paragraphs, add a blank line between them
        if i < len(md_lines) - 1 and is_paragraph(line) and is_paragraph(md_lines[i+1]):
            result_lines.append("")
    
    # Join the result lines
    markdown = '\n'.join(result_lines)
    
    return markdown
