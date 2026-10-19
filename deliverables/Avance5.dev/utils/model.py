
def invoke_and_measure(
    model_id: str,
    system_prompt: str,
    user_message: str,
    bedrock_client,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 2048,
) -> dict:
    """
    Invoke a Bedrock model via the Converse API and return the same operational
    metrics captured in Avance 4: invocation latency, TTFT, token counts, and
    response content.

    Two calls are made:
    - converse(): captures total invocation latency and token usage from native metrics.
    - converse_stream(): captures Time to First Token (TTFT) by timing the first
      contentBlockDelta event.

    Returns a dict with keys:
        model_id, invocation_latency_ms, ttft_ms, input_tokens, output_tokens,
        total_tokens, response_length_chars, response_text, stop_reason,
        temperature, top_p, max_tokens.
    On API error, returns {"error": <message>, "model_id": <model_id>}.
    """
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    system = [{"text": system_prompt}]
    inference_config = {"temperature": temperature, "topP": top_p, "maxTokens": max_tokens}

    # --- Converse: total latency + token usage ---
    t_start = time.time()
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            system=system,
            inferenceConfig=inference_config,
        )
        t_end = time.time()
    except Exception as exc:
        return {"error": str(exc), "model_id": model_id}

    usage = response.get("usage", {})
    metrics = response.get("metrics", {})

    response_text = ""
    for block in response.get("output", {}).get("message", {}).get("content", []):
        if "text" in block:
            response_text += block["text"]

    # --- converse_stream: TTFT ---
    ttft_ms = None
    try:
        t_stream = time.time()
        stream_resp = bedrock_client.converse_stream(
            modelId=model_id,
            messages=messages,
            system=system,
            inferenceConfig=inference_config,
        )
        for event in stream_resp["stream"]:
            if "contentBlockDelta" in event:
                ttft_ms = (time.time() - t_stream) * 1000
                break
    except Exception:
        ttft_ms = None

    return {
        "model_id": model_id,
        "invocation_latency_ms": metrics.get("latencyMs", (t_end - t_start) * 1000),
        "ttft_ms": ttft_ms,
        "input_tokens": usage.get("inputTokens", 0),
        "output_tokens": usage.get("outputTokens", 0),
        "total_tokens": usage.get("totalTokens", 0),
        "response_length_chars": len(response_text),
        "response_text": response_text,
        "stop_reason": response.get("stopReason", "unknown"),
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }


def evaluate_precision(
    agent_response: str,
    expected_output: dict,
    clause_text: str,
    judge_prompt: str,
    judge_model_id: str,
    bedrock_client,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> dict:
    """
    Evaluate the precision of one agent response using an LLM judge.

    Calls invoke_and_measure with the judge model, passing agent_response and
    expected_output as context. Parses the judge's JSON reply into sub-scores.

    Returns a dict with keys:
        precision_score, ranking_score, evidence_score, recommendation_score,
        format_score, ranking_match, judge_reasoning,
        judge_input_tokens, judge_output_tokens, judge_latency_ms.
    On API or parse error, returns {"error": <message>}.
    """
    user_message = (
        f"<clause_evaluated>\n{clause_text}\n</clause_evaluated>\n\n"
        f"<agent_response>\n{agent_response}\n</agent_response>\n\n"
        f"<expected_response>\n{json.dumps(expected_output, indent=2)}\n</expected_response>"
    )

    result = invoke_and_measure(
        model_id=judge_model_id,
        system_prompt=judge_prompt,
        user_message=user_message,
        bedrock_client=bedrock_client,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if "error" in result:
        return result

    raw = result["response_text"]
    try:
        scores = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"error": f"Judge returned unparseable response: {raw[:200]}"}
        scores = json.loads(match.group())

    return {
        **scores,
        "judge_input_tokens": result["input_tokens"],
        "judge_output_tokens": result["output_tokens"],
        "judge_latency_ms": result["invocation_latency_ms"],
    }