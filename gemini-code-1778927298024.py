from agents import Agent, ShellTool, WebSearchTool

# Instantiating a localized GPT-5.1/5.5 agent
coding_agent = Agent(
    name="Custom Jarvis Coder",
    model="gpt-5.5",
    instructions="You are an autonomous systems developer. Implement features, debug the workspace directory, and execute testing scripts.",
    tools=[WebSearchTool(), ShellTool(), apply_patch_tool]
)