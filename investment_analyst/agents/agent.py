"""
Investment Research Analyst multi-agent system.
A team of agents that researches a company, stress-tests an investment thesis
through a loop of analysis and critique, then produces parallel bull/bear cases
before writing a final report to disk.
"""
import logging
import os

import yfinance as yf
import google.cloud.logging
from callback_logging import log_model_response, log_query_to_model
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent
from google.adk.tools.langchain_tool import LangchainTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from langchain_community.tools import WikipediaQueryRun
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.utilities import WikipediaAPIWrapper

cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL")
print(model_name)


# Tools
def append_to_state(
    tool_context: ToolContext, field: str, response: str
) -> dict[str, str]:
    """Append new output to an existing state key.

    Args:
        field (str): a field name to append to
        response (str): a string to append to the field

    Returns:
        dict[str, str]: {"status": "success"}
    """
    existing_state = tool_context.state.get(field, [])
    tool_context.state[field] = existing_state + [response]
    logging.info(f"[Added to {field}] {response}")
    return {"status": "success"}


def get_stock_fundamentals(tool_context: ToolContext, ticker: str) -> dict:
    """Fetch key financial fundamentals for a stock ticker from Yahoo Finance.

    Args:
        ticker (str): stock ticker symbol, e.g. 'AAPL', 'TSLA'

    Returns:
        dict: market cap, P/E ratio, revenue, profit margin, 52-week range
    """
    info = yf.Ticker(ticker).info
    return {
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "revenue": info.get("totalRevenue"),
        "profit_margin": info.get("profitMargins"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "analyst_target_price": info.get("targetMeanPrice"),
        "recommendation": info.get("recommendationKey"),
    }


def write_file(
    tool_context: ToolContext,
    directory: str,
    filename: str,
    content: str,
) -> dict[str, str]:
    target_path = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w") as f:
        f.write(content)
    return {"status": "success"}


# Agents

researcher = Agent(
    name="researcher",
    model=model_name,
    description="Researches a company or stock using Wikipedia.",
    instruction="""
    PROMPT:
    { PROMPT? }

    INVESTMENT_THESIS:
    { INVESTMENT_THESIS? }

    CRITICAL_FEEDBACK:
    { CRITICAL_FEEDBACK? }

    INSTRUCTIONS:
    - If there is CRITICAL_FEEDBACK, use your Wikipedia tool to find facts that
      address the gaps or concerns raised.
    - If there is an INVESTMENT_THESIS already, use your Wikipedia tool to find
      additional supporting or challenging facts.
    - If both are empty, gather foundational facts about the company or asset in
      the PROMPT: its history, business model, key products, leadership, and
      competitive landscape.
    - Use both research tools together for a complete picture:
        * Wikipedia — company history, business model, background
        * YahooFinanceNewsTool — latest financial news headlines
    - Use the 'append_to_state' tool to save your findings to the field 'research'.
    - Summarize the key facts you found.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[
        LangchainTool(tool=WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())),
        LangchainTool(tool=YahooFinanceNewsTool()),
        append_to_state,
    ],
)

analyst = Agent(
    name="analyst",
    model=model_name,
    description="Writes and refines an investment thesis based on research.",
    instruction="""
    PROMPT:
    { PROMPT? }

    RESEARCH:
    { research? }

    INVESTMENT_THESIS:
    { INVESTMENT_THESIS? }

    CRITICAL_FEEDBACK:
    { CRITICAL_FEEDBACK? }

    INSTRUCTIONS:
    - Write a structured investment thesis for the company or asset in the PROMPT.
    - If CRITICAL_FEEDBACK exists, revise the INVESTMENT_THESIS to address those concerns.
    - If RESEARCH is provided, incorporate relevant facts to strengthen the thesis.
    - Before writing, use 'get_stock_fundamentals' with the company's ticker symbol
      to retrieve real financial data (P/E, market cap, revenue, margins, 52-week
      range, analyst target price). Use these numbers in the valuation section.
    - Your thesis must cover:
        1. Business overview (what the company does and its moat)
        2. Growth catalysts (why now is a good time to invest)
        3. Key risks (be honest)
        4. Valuation perspective — use the real figures from get_stock_fundamentals
    - Use the 'append_to_state' tool to save your thesis to the field 'INVESTMENT_THESIS'.
    - Summarize what you changed or focused on in this pass.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[get_stock_fundamentals, append_to_state],
)

devils_advocate = Agent(
    name="devils_advocate",
    model=model_name,
    description="Critiques the investment thesis and decides whether to iterate or escalate.",
    instruction="""
    INVESTMENT_THESIS:
    { INVESTMENT_THESIS? }

    INSTRUCTIONS:
    You are a skeptical senior analyst. Your job is to stress-test the INVESTMENT_THESIS.

    - Identify logical gaps, unsupported claims, ignored risks, or weak reasoning.
    - If the thesis is weak or incomplete (missing key risks, lacks a valuation view,
      or relies on unsupported assumptions), use the 'append_to_state' tool to save
      your specific critique to the field 'CRITICAL_FEEDBACK', then say you are
      sending it back for revision.
    - If the thesis is thorough and well-reasoned (covers moat, catalysts, risks,
      and valuation), respond with the word ESCALATE on its own line to exit the loop.
    - Be concise and specific. Do not repeat praise — only flag real problems.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[append_to_state],
)

bull_case_writer = Agent(
    name="bull_case_writer",
    model=model_name,
    description="Writes the optimistic bull case for the investment.",
    instruction="""
    INVESTMENT_THESIS:
    { INVESTMENT_THESIS? }

    RESEARCH:
    { research? }

    INSTRUCTIONS:
    - Write a compelling, evidence-backed bull case for this investment.
    - Focus on: best-case growth trajectory, strongest competitive advantages,
      tailwinds, and what a successful outcome looks like in 3-5 years.
    - Keep it to 3-4 punchy paragraphs.
    - Use 'append_to_state' to save your bull case to the field 'BULL_CASE'.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[append_to_state],
)

bear_case_writer = Agent(
    name="bear_case_writer",
    model=model_name,
    description="Writes the pessimistic bear case for the investment.",
    instruction="""
    INVESTMENT_THESIS:
    { INVESTMENT_THESIS? }

    RESEARCH:
    { research? }

    INSTRUCTIONS:
    - Write a sober, honest bear case for this investment.
    - Focus on: key risks that could derail the thesis, competitive threats,
      macro headwinds, and what a bad outcome looks like in 3-5 years.
    - Keep it to 3-4 punchy paragraphs.
    - Use 'append_to_state' to save your bear case to the field 'BEAR_CASE'.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[append_to_state],
)

report_writer = Agent(
    name="report_writer",
    model=model_name,
    description="Aggregates all research and analysis into a final investment report file.",
    instruction="""
    PROMPT:
    { PROMPT? }

    INVESTMENT_THESIS:
    { INVESTMENT_THESIS? }

    BULL_CASE:
    { BULL_CASE? }

    BEAR_CASE:
    { BEAR_CASE? }

    INSTRUCTIONS:
    - Create a professional investment report title based on the company in PROMPT
      (e.g. "Tesla_Investment_Report").
    - Use the 'write_file' tool with:
        - directory: 'investment_reports'
        - filename: the report title as a .txt file
        - content: a structured report containing:
            INVESTMENT THESIS
            ─────────────────
            { INVESTMENT_THESIS content }

            BULL CASE
            ─────────
            { BULL_CASE content }

            BEAR CASE
            ─────────
            { BEAR_CASE content }
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[write_file],
)

# Orchestration

research_team = LoopAgent(
    name="research_team",
    description="Iteratively researches and stress-tests an investment thesis.",
    sub_agents=[researcher, analyst, devils_advocate],
    max_iterations=3,
)

case_writers = ParallelAgent(
    name="case_writers",
    description="Simultaneously writes the bull and bear cases.",
    sub_agents=[bull_case_writer, bear_case_writer],
)

investment_research_team = SequentialAgent(
    name="investment_research_team",
    description="Full investment research pipeline: loop analysis then parallel cases then report.",
    sub_agents=[research_team, case_writers, report_writer],
)

root_agent = Agent(
    name="greeter",
    model=model_name,
    description="Welcomes the user and kicks off the investment research workflow.",
    instruction="""
    - Greet the user and let them know you are an investment research assistant that
      will produce a full research report on any publicly known company or asset.
    - Ask them: which company or stock would you like us to research?
    - When they respond, use the 'append_to_state' tool to store their answer in the
      'PROMPT' state key, then transfer to the 'investment_research_team' agent.
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0),
    tools=[append_to_state],
    sub_agents=[investment_research_team],
)
