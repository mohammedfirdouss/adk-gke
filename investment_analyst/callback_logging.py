"""
Provides helper functions for observability. Handles formatting and sending
agent queries, responses, and tool calls to Google Cloud Logging to aid
in monitoring and debugging.
"""
import logging

import google.cloud.logging
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse

_client = google.cloud.logging.Client()
_client.setup_logging()


def log_query_to_model(callback_context: CallbackContext, llm_request: LlmRequest):
    if llm_request.contents and llm_request.contents[-1].role == "user":
        parts = llm_request.contents[-1].parts
        if parts and parts[0].text:
            logging.info(f"[query to {callback_context.agent_name}]: {parts[0].text}")


def log_model_response(callback_context: CallbackContext, llm_response: LlmResponse):
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.text:
                logging.info(f"[response from {callback_context.agent_name}]: {part.text}")
            elif part.function_call:
                logging.info(f"[function call from {callback_context.agent_name}]: {part.function_call.name}")
