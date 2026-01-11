# Architecture Diagrams

This directory contains PlantUML diagrams documenting the system architecture and workflows.

## 📊 Diagram Files

| File | Description | Purpose |
|------|-------------|---------|
| **architecture.puml** | Complete system architecture | Shows all components, data sources, storage, and application layers |
| **data_flow.puml** | Product ingestion workflow | Step-by-step flow from file picker to Elasticsearch indexing |
| **api_flow.puml** | REST API request sequences | Product ingestion, retrieval, and missing attributes queries |
| **incident_flow.puml** | Supplier incident tracking | Incident logging, KPI calculations, and dashboard analytics |
| **deployment.puml** | Deployment environments | Development setup and production architecture (future) |

## 🎨 Viewing the Diagrams

### Online Viewers

1. **PlantUML Online Server**
   - Visit: https://www.plantuml.com/plantuml/uml/
   - Paste diagram code
   - View rendered diagram

2. **GitHub Integration**
   - Install PlantUML extension for GitHub
   - Diagrams render automatically in README files

3. **VS Code Extension**
   - Install "PlantUML" extension by jebbs
   - Open `.puml` file
   - Press `Alt+D` to preview

### Local Rendering

**Prerequisites:**
```bash
# Install Java (required for PlantUML)
java --version

# Install Graphviz (for layout)
# Windows: choco install graphviz
# Mac: brew install graphviz
# Linux: sudo apt-get install graphviz

# Install PlantUML
# Download plantuml.jar from https://plantuml.com/download
```

**Generate PNG/SVG:**
```bash
# Generate PNG
java -jar plantuml.jar architecture.puml

# Generate SVG
java -jar plantuml.jar -tsvg architecture.puml

# Generate all diagrams
java -jar plantuml.jar *.puml

# With custom output directory
java -jar plantuml.jar -o ../docs/images *.puml
```

### VS Code Setup

1. Install extensions:
   - PlantUML (by jebbs)
   - Graphviz Preview (optional)

2. Configure settings.json:
   ```json
   {
     "plantuml.exportFormat": "svg",
     "plantuml.exportSubFolder": false,
     "plantuml.exportOutDir": "docs/images"
   }
   ```

3. Keyboard shortcuts:
   - `Alt+D`: Preview diagram
   - `Ctrl+Shift+P` → "PlantUML: Export Current Diagram"

## 📝 Diagram Syntax Reference

### Color Palette Used

```plantuml
!define LIGHTORANGE #FFE0B2  ' Application Layer
!define LIGHTBLUE #B3E5FC    ' Elasticsearch
!define LIGHTGREEN #C8E6C9   ' Core Modules
!define LIGHTPURPLE #E1BEE7  ' Services
!define LIGHTYELLOW #FFF9C4  ' Data Sources
!define LIGHTRED #FFCDD2     ' Errors
```

### Common Elements

**Components:**
```plantuml
component "Component Name" as Alias #COLOR
participant "Participant" as P
actor "User" as U
database "Database" as DB
file "File" as F
```

**Connections:**
```plantuml
A -> B : Synchronous call
A --> B : Return/response
A ..> B : Async/optional
A ->> B : Message
```

### Diagram Types

1. **Component Diagram** (architecture.puml)
   - Shows system structure
   - Components and relationships
   - Data flow arrows

2. **Activity Diagram** (data_flow.puml)
   - Step-by-step processes
   - Decision points (if/else)
   - Swimlanes for actors

3. **Sequence Diagram** (api_flow.puml, incident_flow.puml)
   - Time-based interactions
   - Request/response patterns
   - Alternative flows

4. **Deployment Diagram** (deployment.puml)
   - Physical/logical deployment
   - Nodes and artifacts
   - Network connections

## 🔄 Updating Diagrams

When updating architecture:

1. **Edit `.puml` files** in this directory
2. **Regenerate images** (if needed for documentation)
3. **Update ARCHITECTURE.md** if major changes
4. **Commit both `.puml` and generated images**

### Best Practices

- ✅ Use consistent color coding
- ✅ Add notes for important details
- ✅ Keep diagrams focused (one concept per diagram)
- ✅ Use clear, descriptive labels
- ✅ Include legends when needed
- ✅ Version control `.puml` sources, not just images

## 📚 PlantUML Resources

- **Official Documentation**: https://plantuml.com/
- **Cheat Sheet**: https://ogom.github.io/draw_uml/plantuml/
- **Component Diagrams**: https://plantuml.com/component-diagram
- **Sequence Diagrams**: https://plantuml.com/sequence-diagram
- **Activity Diagrams**: https://plantuml.com/activity-diagram-beta
- **Deployment Diagrams**: https://plantuml.com/deployment-diagram

## 🎯 Use Cases for Each Diagram

### architecture.puml
**Use when:**
- Onboarding new developers
- Explaining system overview to stakeholders
- Planning new integrations
- Documenting component dependencies

### data_flow.puml
**Use when:**
- Troubleshooting ingestion issues
- Understanding data transformation steps
- Explaining the file picker workflow
- Planning data pipeline optimizations

### api_flow.puml
**Use when:**
- Implementing new API clients
- Debugging API request/response issues
- Understanding validation flow
- Writing API documentation

### incident_flow.puml
**Use when:**
- Training operators on incident logging
- Understanding KPI calculations
- Debugging analytics queries
- Planning dashboard enhancements

### deployment.puml
**Use when:**
- Setting up development environment
- Planning production deployment
- Documenting infrastructure requirements
- Designing high availability setup

---

**Tip**: Always keep diagrams in sync with code. Update them during code reviews and feature implementations.
