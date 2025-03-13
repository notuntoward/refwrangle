## Points
- Recommended reading in SQL course: [Lawrence, 2022](zotero://select/library/items/B7TNABNU)
- clear graph of a set of foreign keys
## SQL
- big list of SQL variants
- scales "vertically": make a single server bigger
- ACID stingent security complant (always)
- SQL use cases
	- ACID required by regulations
	- transactional
	- enterprise resource planning e.g. supply chain, human resources,…
## NoSQL
- not always SQL (can do SQL too)
- scaled "horizontally": I think this means can expand by adding a new compute node
- use when data changes fast, must be scalable, and when it's non-structured
- usually doesn't meet stringent ACID standards
	- SQL often does
	- some NoSQL does e.g. Mongo's
- big list of NoSQL types
	- Document
	- Key-value
	- Column-family stores
	- Graph
- NoSQL use cases
	- transactional (can just do internal SQL-type tables), or when store unstructured
	- document and digital assets management
	- graph and network analysis
	- IoT