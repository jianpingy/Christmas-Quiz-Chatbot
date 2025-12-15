import os
import gradio as gr
from crewai import Agent, Task, Crew, Process, LLM

# --- 1. Configuration ---
# Ensure WATSONX_APIKEY, WATSONX_PROJECT_ID, and WATSONX_URL are set
# os.environ["WATSONX_APIKEY"] = os.getenv("WATSONX_APIKEY", "")
# os.environ["WATSONX_PROJECT_ID"] = os.getenv("WATSONX_PROJECT_ID", "")
# os.environ["WATSONX_URL"] = os.getenv("WATSONX_URL", "")
watsonx_llm = LLM(model="watsonx/ibm/granite-3-8b-instruct", temperature=0.7)


# --- 2. Agent Definitions (Researcher, Host, Santa) ---
noel_researcher = Agent(
    role='Christmas Folklore Historian',
    goal='Discover obscure Christmas facts based on a category.',
    backstory="You are an expert in global traditions.",
    llm=watsonx_llm
)
holly_host = Agent(
    role='Head Elf of Entertainment',
    goal='Turn facts into a festive MCQ with a ||| separator.',
    backstory="You are a high-energy game show host elf.",
    llm=watsonx_llm
)
santa_judge = Agent(
    role='Santa Claus',
    goal='Validate answers and spread Christmas cheer.',
    backstory="You are Santa. You check the Nice List.",
    llm=watsonx_llm
)

# --- 3. Logic Functions ---
def generate_christmas_challenge(category):
    task_research = Task(description=f"Find one specific Christmas fact about {category}.", expected_output="A summary.", agent=noel_researcher)
    
    question_task_format = """Create MCQ. Format:
[Question]: 

A)
B)
C)
D)

||| [Answer Letter]: [Fact]
"""
    task_format = Task(description=question_task_format, expected_output="Question block separated by |||", agent=holly_host, context=[task_research])
    crew = Crew(agents=[noel_researcher, holly_host], tasks=[task_research, task_format])
    return str(crew.kickoff())

def ask_santa(user_input, secret_key):
    task_judge = Task(description=f"User answered '{user_input}'. Truth is '{secret_key}'. Reply as Santa.", expected_output="Santa's response.", agent=santa_judge)
    crew = Crew(agents=[santa_judge], tasks=[task_judge])
    return str(crew.kickoff())

# --- 4. UI Format and Logic ---
def format_question_card(text):
    """Wraps the question in a festive Markdown card."""
    return f"""
<div style="border: 2px solid #2e7d32; border-radius: 15px; padding: 20px; background-color: #f1f8e9; color: #1b5e20;">
    <h2 style="margin-top: 0;">🎄 Christmas Challenge</h2>
    {text.replace('|||', '').strip()}
</div>
"""

def format_santa_card(text):
    """Wraps Santa's response in a parchment-style card."""
    return f"""
<div style="border: 2px dashed #d32f2f; border-radius: 15px; padding: 20px; background-color: #fff5f5; color: #b71c1c;">
    <h2 style="margin-top: 0;">🎅 Santa's Verdict</h2>
    {text}
</div>
"""

def game_logic(user_message, category, history, state):
    if state is None: state = {'status': 'IDLE', 'secret_key': ''}
    if history is None: history = []

    # If message is empty (from a button click), provide a default
    input_text = user_message if user_message else "Let's play!"

    if state['status'] == 'IDLE':
        history.append({"role": "user", "content": input_text})
        history.append({"role": "assistant", "content": f"✨ *Consulting the North Pole library for {category}...*"})
        yield history, state, gr.update(visible=False), gr.update(visible=False)
        
        full_output = generate_christmas_challenge(category)
        parts = full_output.split("|||")
        public_q = parts[0].strip() if len(parts) > 1 else full_output
        state['secret_key'] = parts[1].strip() if len(parts) > 1 else "Hidden"
        state['status'] = 'WAITING_FOR_ANSWER'
        
        history[-1] = {"role": "assistant", "content": format_question_card(public_q)}
        # Hide start/next, show text box for answer
        yield history, state, gr.update(visible=False), gr.update(visible=False)

    elif state['status'] == 'WAITING_FOR_ANSWER':
        history.append({"role": "user", "content": input_text})
        history.append({"role": "assistant", "content": "Checking the Nice List... 📝"})
        yield history, state, gr.update(visible=False), gr.update(visible=False)
        
        verdict = ask_santa(input_text, state['secret_key'])
        state['status'] = 'IDLE'
        
        history[-1] = {"role": "assistant", "content": format_santa_card(verdict)}
        # Show 'Next Challenge' button now that we are IDLE
        yield history, state, gr.update(visible=False), gr.update(visible=True)

# --- 5. "Heavier & Grayer" Snowfall Script ---
snow_js = """
function createSnow() {
    const s = document.createElement('style');
    s.innerHTML = `.sn { color: #a0a0a0; position: fixed; top: -10%; z-index: 9999; animation: f 8s linear infinite; pointer-events: none; } @keyframes f { to { top: 100vh; } }`;
    document.head.appendChild(s);
    setInterval(() => {
        const b = document.createElement('div');
        b.className = 'sn'; b.innerHTML = '❄';
        b.style.left = Math.random() * 100 + 'vw';
        b.style.fontSize = (Math.random() * 15 + 15) + 'px'; // Larger flakes
        b.style.opacity = Math.random() * 0.8 + 0.2; // More opaque
        document.body.appendChild(b);
        setTimeout(() => b.remove(), 8000);
    }, 150); // Faster interval for "heavier" snow
}
setTimeout(createSnow, 1000);
"""

# --- 6. Interface Assembly ---
santa_css = """
.gradio-container {
    background-image: url('https://www.transparenttextures.com/patterns/snow.png'), 
                      linear-gradient(rgba(255,255,255,0.8), rgba(255,255,255,0.8)),
                      url('https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/HPVuGgmOV81JMulqTtrukQ/santa.png');
    background-size: cover;
    background-attachment: fixed;
}
"""

with gr.Blocks(head=f"<script>{snow_js}</script>", css=santa_css, theme=gr.themes.Soft()) as demo:
    gr.HTML("<h1 style='text-align: center; color: #d32f2f;'>❄️ The Christmas Workshop ❄️</h1>")
    
    with gr.Row():
        category_drop = gr.Dropdown(label="Category", choices=["Traditions", "Food", "Clothing", "Myths", "Music"], value="Traditions")
        start_btn = gr.Button("🚀 Start Workshop", variant="primary")
        next_btn = gr.Button("🎁 Next Challenge", visible=False)
    
    chatbot = gr.Chatbot(height=450)
    msg = gr.Textbox(label="Your Answer", placeholder="Type A, B, C, or D...")
    state = gr.State({'status': 'IDLE', 'secret_key': ''})

    # Logic Triggers
    start_btn.click(game_logic, [gr.State("Start"), category_drop, chatbot, state], [chatbot, state, start_btn, next_btn])
    next_btn.click(game_logic, [gr.State("Next"), category_drop, chatbot, state], [chatbot, state, start_btn, next_btn])
    msg.submit(game_logic, [msg, category_drop, chatbot, state], [chatbot, state, start_btn, next_btn])
    msg.submit(lambda: "", None, msg)

if __name__ == "__main__":
    demo.launch()
