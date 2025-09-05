import os
import json
import textwrap
from pathlib import Path
from langchain_mistralai import ChatMistralAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import tool
from langchain.agents import initialize_agent, AgentType
from langchain.schema import Document

# Set the Mistral API key
os.environ["MISTRAL_API_KEY"] = "1QJOIuK9SIhpKkF9vwg3IMgMIiEr0fQR"

# Initialize the ChatMistralAI model
llm = ChatMistralAI(model="codestral-latest")

# Global variables for context management
project_context = {}
file_contents = {}
search_index = {}  # Simple search index

def load_requirements():
    """Load the decoupled requirements from JSON file."""
    try:
        with open("decoupled_requirements.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ decoupled_requirements.json not found!")
        return None

def create_project_structure(requirements):
    """Create the fixed folder structure based on requirements."""
    project_name = requirements.get("project_name", "generated_project").replace(" ", "_").lower()
    base_path = Path(project_name)

    # Create main directories
    directories = [
        base_path,
        base_path / "src",
        base_path / "tests",
        base_path / "docs",
        base_path / "config"
    ]

    # Add component-specific directories
    components = requirements.get("localhost_implementation", {}).get("components", [])
    for component in components:
        if "frontend" in component.lower():
            directories.extend([
                base_path / "src" / "frontend",
                base_path / "src" / "frontend" / "components",
                base_path / "src" / "frontend" / "pages",
                base_path / "src" / "frontend" / "utils"
            ])
        elif "backend" in component.lower():
            directories.extend([
                base_path / "src" / "backend",
                base_path / "src" / "backend" / "routes",
                base_path / "src" / "backend" / "models",
                base_path / "src" / "backend" / "controllers"
            ])

    # Create directories
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # Create basic files
    create_basic_files(base_path, requirements)

    return base_path

def create_basic_files(base_path, requirements):
    """Create basic project files."""
    files_to_create = {
        "README.md": f"""# {requirements.get('project_name', 'Generated Project')}

{requirements.get('description', 'Auto-generated project')}

## Setup

### Prerequisites
- Docker
- Docker Compose (if using multiple services)

### Quick Start with Docker

```bash
# Build and run with Docker
docker build -t {requirements.get('project_name', 'app').lower().replace(' ', '-')} .
docker run -p 3000:3000 {requirements.get('project_name', 'app').lower().replace(' ', '-')}
```

### Development

```bash
# Install dependencies
npm install

# Run development server
npm start
```

## Run
""",
        "requirements.txt": "# Python dependencies\n",
        "package.json": '{"name": "generated-project", "version": "1.0.0", "description": "", "main": "index.js", "scripts": {"start": "node index.js"}, "dependencies": {}}',
        ".gitignore": "node_modules/\n__pycache__/\n*.pyc\n.env\n",
        "src/__init__.py": "",
        "tests/__init__.py": ""
    }

    for file_path, content in files_to_create.items():
        full_path = base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    # Generate Docker files
    generate_docker_files(base_path, requirements)

def generate_docker_files(base_path, requirements):
    """Generate Dockerfile and docker-compose.yml if needed."""
    components = requirements.get("localhost_implementation", {}).get("components", [])
    has_frontend = any("react" in comp.lower() or "frontend" in comp.lower() for comp in components)
    has_backend = any("node" in comp.lower() or "express" in comp.lower() or "backend" in comp.lower() for comp in components)
    has_database = any("sqlite" in comp.lower() or "database" in comp.lower() for comp in components)

    # Always generate Dockerfile
    dockerfile_content = generate_dockerfile(components)
    dockerfile_path = base_path / "Dockerfile"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    # Generate docker-compose.yml if multiple services
    if (has_frontend and has_backend) or has_database:
        compose_content = generate_docker_compose(components, has_frontend, has_backend, has_database)
        compose_path = base_path / "docker-compose.yml"
        with open(compose_path, "w") as f:
            f.write(compose_content)

def generate_dockerfile(components):
    """Generate appropriate Dockerfile based on components."""
    has_frontend = any("react" in comp.lower() or "frontend" in comp.lower() for comp in components)
    has_backend = any("node" in comp.lower() or "express" in comp.lower() or "backend" in comp.lower() for comp in components)

    if has_frontend and has_backend:
        # Full-stack application
        return """# Multi-stage build for full-stack application
FROM node:18-alpine AS base

# Backend stage
FROM base AS backend
WORKDIR /app/backend
COPY src/backend/package*.json ./
RUN npm install
COPY src/backend/ .

# Frontend stage
FROM base AS frontend
WORKDIR /app/frontend
COPY src/frontend/package*.json ./
RUN npm install
COPY src/frontend/ .

# Production stage
FROM node:18-alpine AS production
WORKDIR /app

# Copy backend
COPY --from=backend /app/backend ./backend
COPY --from=backend /app/backend/node_modules ./backend/node_modules

# Copy frontend build
COPY --from=frontend /app/frontend ./frontend
COPY --from=frontend /app/frontend/node_modules ./frontend/node_modules

# Install serve for frontend
RUN npm install -g serve

EXPOSE 5000 3000
CMD ["sh", "-c", "cd backend && npm start & cd ../frontend && npm run build && serve -s build -l 3000"]
"""
    elif has_backend:
        # Backend-only application
        return """FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 5000
CMD ["npm", "start"]
"""
    elif has_frontend:
        # Frontend-only application
        return """FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 3000
CMD ["npm", "start"]
"""
    else:
        # Default Node.js application
        return """FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 3000
CMD ["npm", "start"]
"""

def generate_docker_compose(components, has_frontend, has_backend, has_database):
    """Generate docker-compose.yml for multi-service applications."""
    services = {}

    if has_backend:
        services['backend'] = {
            'build': '.',
            'ports': ['5000:5000'],
            'volumes': ['./src/backend:/app/src/backend'],
            'environment': ['NODE_ENV=development']
        }

    if has_frontend:
        services['frontend'] = {
            'build': '.',
            'ports': ['3000:3000'],
            'volumes': ['./src/frontend:/app/src/frontend'],
            'depends_on': ['backend'] if has_backend else []
        }

    if has_database:
        services['database'] = {
            'image': 'sqlite3:latest',
            'volumes': ['./data:/data'],
            'command': 'sqlite3 /data/tasks.db'
        }

    compose = {
        'version': '3.8',
        'services': services
    }

    # Convert to YAML-like string
    yaml_content = "version: '3.8'\n\nservices:\n"

    for service_name, service_config in services.items():
        yaml_content += f"  {service_name}:\n"
        for key, value in service_config.items():
            if isinstance(value, list):
                yaml_content += f"    {key}:\n"
                for item in value:
                    yaml_content += f"      - {item}\n"
            else:
                yaml_content += f"    {key}: {value}\n"
        yaml_content += "\n"

    return yaml_content

# Custom tools for the agent
@tool
def read_file_tool(file_path: str) -> str:
    """Read the contents of a file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
            file_contents[file_path] = content
            return content
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file_tool(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        file_contents[file_path] = content
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def search_code_tool(query: str) -> str:
    """Search for code patterns in the project."""
    results = []
    for file_path, content in file_contents.items():
        if query.lower() in content.lower():
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if query.lower() in line.lower():
                    results.append(f"{file_path}:{i+1}: {line.strip()}")

    return "\n".join(results[:10]) if results else "No matches found"

@tool
def list_directory_tool(path: str) -> str:
    """List contents of a directory."""
    try:
        items = list(Path(path).iterdir())
        return "\n".join([str(item) for item in items])
    except Exception as e:
        return f"Error listing directory: {e}"

def create_code_generation_chain():
    """Create the code generation chain."""
    template = """
You are an expert code generator. Generate code for the file: {file_path}

CRITICAL REQUIREMENTS:
• Generate ONLY clean, valid code without comments at the top
• Do NOT include file paths or language markers in the code
• Ensure proper imports and syntax
• Match API contracts exactly with other components
• Include error handling and best practices
• For React files, include proper JSX syntax
• For CSS files, provide only CSS code
• For backend files, include proper Node.js/Express patterns

Project Context: {project_context}
Requirements: {requirements}
Implementation Plan: {implementation_plan}

Current Task: {current_task}
File Purpose: {file_purpose}

Generate complete, working code for this file. Consider:
- Dependencies and imports
- Error handling
- Best practices
- Integration with other components
- The specific requirements and assumptions

IMPORTANT: Return ONLY the executable code, no explanations or markdown formatting.
"""

    prompt = PromptTemplate(
        input_variables=["file_path", "project_context", "requirements", "implementation_plan", "current_task", "file_purpose"],
        template=template
    )

    chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
    return chain

def generate_file_code(chain, file_path, requirements, current_task, file_purpose):
    """Generate code for a specific file."""
    project_context_str = json.dumps(project_context, indent=2)
    requirements_str = json.dumps(requirements, indent=2)
    implementation_plan = requirements.get("implementation_plan", [])

    code = chain.run(
        file_path=file_path,
        project_context=project_context_str,
        requirements=requirements_str,
        implementation_plan=implementation_plan,
        current_task=current_task,
        file_purpose=file_purpose
    )

    return code

def setup_search_index():
    """Setup simple search index for context search."""
    global search_index
    search_index = {}

def update_search_index(file_path, content):
    """Update search index with new file content."""
    global search_index
    words = content.lower().split()
    for word in words:
        if word not in search_index:
            search_index[word] = []
        if file_path not in search_index[word]:
            search_index[word].append(file_path)

def main():
    """Main function to run the coder agent."""
    print("🤖 Coder Agent Starting...")

    # Load requirements
    requirements = load_requirements()
    if not requirements:
        return

    print(f"📋 Loaded requirements for: {requirements.get('project_name')}")

    # Create project structure
    project_path = create_project_structure(requirements)
    print(f"📁 Created project structure at: {project_path}")

    # Setup global context
    global project_context
    project_context = requirements

    # Setup search index
    setup_search_index()

    # Create code generation chain
    code_chain = create_code_generation_chain()

    # Generate files based on implementation plan
    implementation_plan = requirements.get("implementation_plan", [])

    for i, task in enumerate(implementation_plan):
        print(f"\n🔧 Task {i+1}: {task}")

        # Determine which file to create/modify
        file_path = determine_file_for_task(task, project_path, requirements)

        if file_path:
            print(f"📝 Generating: {file_path}")

            # Generate code
            file_purpose = f"Implement {task}"
            code = generate_file_code(code_chain, str(file_path), requirements, task, file_purpose)

            # Clean up the code (remove markdown formatting and invalid syntax)
            code = code.replace("```python", "").replace("```javascript", "").replace("```jsx", "").replace("```css", "").replace("```", "").strip()
            
            # Remove any file path comments at the top
            lines = code.split('\n')
            cleaned_lines = []
            for line in lines:
                if not line.startswith('# ') or not '/' in line:
                    cleaned_lines.append(line)
            
            code = '\n'.join(cleaned_lines).strip()

            # Write the file directly
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(code)
            file_contents[str(file_path)] = code

            # Update search index
            update_search_index(str(file_path), code)

            print(f"✅ Generated {file_path}")

    print("\n🎉 Code generation complete!")
    print(f"📂 Project created at: {project_path}")

def determine_file_for_task(task, project_path, requirements):
    """Determine which file to create/modify for a given task."""
    task_lower = task.lower()

    # Frontend files
    if "react" in task_lower or "frontend" in task_lower or "ui" in task_lower:
        if "component" in task_lower:
            return project_path / "src" / "frontend" / "components" / "TaskList.jsx"
        elif "page" in task_lower:
            return project_path / "src" / "frontend" / "pages" / "Home.jsx"
        else:
            return project_path / "src" / "frontend" / "App.jsx"

    # Backend files
    elif "backend" in task_lower or "api" in task_lower or "server" in task_lower:
        if "route" in task_lower or "endpoint" in task_lower:
            return project_path / "src" / "backend" / "routes" / "tasks.js"
        elif "model" in task_lower:
            return project_path / "src" / "backend" / "models" / "Task.js"
        else:
            return project_path / "src" / "backend" / "server.js"

    # Database files
    elif "database" in task_lower or "sqlite" in task_lower:
        return project_path / "src" / "backend" / "models" / "database.js"

    # Default to main application file
    else:
        components = requirements.get("localhost_implementation", {}).get("components", [])
        if any("react" in comp.lower() for comp in components):
            return project_path / "src" / "frontend" / "App.jsx"
        else:
            return project_path / "src" / "backend" / "server.js"

if __name__ == "__main__":
    main()
