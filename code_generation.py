import os
import json
import textwrap
import re
from langchain_mistralai import ChatMistralAI

# Set the Mistral API key
os.environ["MISTRAL_API_KEY"] = "1QJOIuK9SIhpKkF9vwg3IMgMIiEr0fQR"

# Initialize the ChatMistralAI model with Codestral
model = ChatMistralAI(model="codestral-latest")

def ask_user(question: str) -> str:
    """Prompt appears for user input."""
    return input(f"\n🤖 {question}\n👤 ").strip()

def extract_code_or_json(response: str):
    """Extract JSON requirements document from response."""
    # Try to extract JSON
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # Try to extract JSON without code blocks
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    return response

def chat_with_history(messages):
    """Chat with conversation history."""
    response = model.invoke(messages)
    return response.content

# System prompt for conversational requirements decoupling
SYSTEM_PROMPT = textwrap.dedent("""
You are an expert software architect specializing in decoupling requirements for localhost-makable applications.

CODE QUALITY REQUIREMENTS:
• Generate ONLY valid, executable code without syntax errors
• Ensure API contracts match between frontend and backend
• Include proper error handling and user feedback
• Create separate files for different languages (JSX, CSS, JS)
• Use consistent naming conventions and best practices
• Include necessary imports and dependencies
• Add comments for complex logic
• Ensure cross-platform compatibility

SMART ASSUMPTIONS FOR SIMPLE REQUESTS:
• If user says "simple", assume minimal viable product with basic CRUD operations
• Use SQLite for database, no authentication, single-user application
• Choose popular, beginner-friendly tech stack (React/Flask/Node.js)
• Don't ask unnecessary questions - make reasonable assumptions
• Focus on core functionality only, avoid over-engineering

Your task is to analyze user requests and create DETAILED REQUIREMENTS DOCUMENTS that:
1. Break down the request into core functionality vs external dependencies
2. Identify all assumptions and external services needed
3. Provide implementation plans that can run on localhost
4. Suggest mock implementations for external dependencies
5. Create modular, decoupled architecture designs

CONVERSATION STYLE:
• For "simple" requests: Make assumptions and proceed quickly
• Ask ONE concise question at a time if anything is unclear
• When ready, output a comprehensive requirements document in JSON format
• Focus on decoupling and localhost feasibility
• Be conversational and helpful

OUTPUT FORMAT: When ready, provide a JSON object with:
{
  "project_name": "string",
  "core_requirements": ["list of core features"],
  "external_dependencies": ["list of external services/APIs"],
  "localhost_implementation": {
    "architecture": "description",
    "components": ["list of components"],
    "data_flow": "description"
  },
  "mock_strategies": {
    "external_service": "mock implementation approach"
  },
  "implementation_plan": ["step-by-step plan"],
  "assumptions": ["list of assumptions made"]
}
""").strip()

def interactive_code_generation(initial_prompt: str, max_turns: int = 20):
    """Interactive conversation for requirements generation."""
    history = [
        ("system", SYSTEM_PROMPT),
        ("user", initial_prompt)
    ]
    
    print("🤖 Welcome to the Interactive Requirements Agent!")
    print("I'll help you define requirements through conversation.")
    
    # Detect if this is a simple request
    is_simple = 'simple' in initial_prompt.lower() or len(initial_prompt.split()) < 10
    
    if is_simple:
        print("🤖 Detected simple request - I'll make reasonable assumptions and proceed quickly!")
        max_turns = 3  # Limit questions for simple requests
    
    for turn in range(max_turns):
        print(f"--- Turn {turn + 1} ---")
        
        # Get AI response
        response = chat_with_history(history)
        print(f"🤖 {response}")
        
        # Check if response contains JSON requirements document
        extracted = extract_code_or_json(response)
        if isinstance(extracted, dict) and 'project_name' in extracted:
            print("\n📄 Requirements Document Generated!")
            approval = ask_user("✅ Approve this requirements document? (yes / no / modify)")
            if approval.lower() == 'yes':
                return extracted
            elif approval.lower() == 'modify':
                clarification = ask_user("What changes would you like to the requirements?")
                history.append(("assistant", response))
                history.append(("user", f"Please modify requirements: {clarification}"))
                continue
            else:
                clarification = ask_user("What additional requirements or changes do you need?")
                history.append(("assistant", response))
                history.append(("user", clarification))
                continue
        
        # Continue conversation
        user_response = ask_user("Your response:")
        history.append(("assistant", response))
        history.append(("user", user_response))
    
    print("Reached maximum turns. Here's the final response:")
    return chat_with_history(history)

if __name__ == "__main__":
    initial_prompt = input("📝 Describe the application you want requirements for:\n> ").strip()
    
    result = interactive_code_generation(initial_prompt)
    
    print("\n🎉 Final Requirements Document:")
    if isinstance(result, dict):
        print(json.dumps(result, indent=2))
    else:
        print(result)
    
    # Save to file
    with open("decoupled_requirements.json", "w") as f:
        if isinstance(result, dict):
            json.dump(result, f, indent=2)
        else:
            f.write(str(result))
    print("\n💾 Saved to decoupled_requirements.json")
