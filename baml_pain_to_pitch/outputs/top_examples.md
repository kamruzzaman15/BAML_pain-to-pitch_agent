# BAML Pain-to-Pitch — Top Examples

Best leads produced by the agent. Each one shows the public pain signal, the model's diagnosis, an illustrative BAML-style rewrite, and a human-reviewable outreach draft.


---

## Example 1: justLV/onju-voice

- **Source file:** https://github.com/justLV/onju-voice/blob/0dbcb106c50622e02702c9425672523b1bc6aa4e/server/llm.py
- **Language:** Jupyter Notebook
- **Pain type:** retry_logic  |  **Use case:** chatbot
- **Pain score:** 5/5  |  **Confidence:** 1.0  |  **Lead score:** 4.65
- **Why BAML may help:** BAML would help by automating the process of retrying failed requests, handling exceptions gracefully, and ensuring that the structured output from the language model is correctly parsed without manual intervention.

### Original brittle code

```
from datetime import datetime, timedelta
from dateutil import tz

import openai
from rich import print

import devices

openai.api_key = os.getenv("OPENAI_API_KEY")

class OpenAIFunctionCalling:
    def __init__(self, config):
        self.config = config
        self.functions = self.setup_functions()

    def call_gpt_retry(self, device, max_retries=4, include_functions=False):
        wait_time = 0.5
        for attempt in range(max_retries):
            try:
                if(include_functions):
                    response = openai.ChatCompletion.create(
                        model=self.config['llm']['gpt_model'],
                        messages=device.messages,
                        functions=self.functions,
                        max_tokens=300,
                    )
                else:
                    response = openai.ChatCompletion.create(
                        model=self.config['llm']['gpt_model'],
                        messages=device.messages,
                        max_tokens=150,
                    )
                return (True, response)
            except Exception as e:
                device.log.error(f"Attempt {attempt+1} of {max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2  # backoff
                else:
                    return (False, e)
```

### Agent diagnosis

The code snippet includes an explicit call to `openai.ChatCompletion.create` with messages, which is a clear indication of an interaction with a language model. The pain in this case is the presence of retry logic around the LLM response parsing, including try/except blocks and exponential backoff for retries. This brittleness is indicative of unreliable structured output from the LLM.

### Illustrative BAML-style rewrite

```
// Define the typed result as a BAML class
class ChatCompletionResult {
  success bool
  response any
}

// Define a BAML function with a client and a prompt
function CallGPTRetry(device: Device, max_retries int = 4, include_functions bool = false) -> ChatCompletionResult {
  client "openai/gpt-3.5-turbo"
  prompt #"""
    You are an assistant that handles retries for GPT API calls.
    Return the success status and response.

    Device: {{ device }}
    Max Retries: {{ max_retries }}
    Include Functions: {{ include_functions }}
  ""#}
}
```

**Client usage:**

```
result = CallGPTRetry(device, max_retries=4, include_functions=True)
if result.success:
  print(result.response)
else:
  print(f'Failed after {max_retries} attempts')
```

_Limits:_ This BAML rewrite assumes that the `Device` class and its attributes are already defined elsewhere in the codebase. It also assumes that the `openai/gpt-3.5-turbo` model is available for use.

### Outreach draft (for human review)

> This looked like an area where BAML could simplify things. By automating retries and handling exceptions, you might find the code cleaner and more maintainable.

_Tone check:_ helpful


---

## Example 2: MewCo-AI/ai_virtual_mate_comm

- **Source file:** https://github.com/MewCo-AI/ai_virtual_mate_comm/blob/459d00bf6c9170d89a087f2db8c3b2140f192696/llm.py
- **Language:** Python
- **Pain type:** retry_logic  |  **Use case:** chatbot
- **Pain score:** 4/5  |  **Confidence:** 0.95  |  **Lead score:** 4.45
- **Why BAML may help:** BAML can automatically parse and validate the structured output from language models, eliminating the need for manual parsing, try/except blocks, and regex cleanup. It ensures that the output is correctly formatted and ready for use without additional code.

### Original brittle code

```
elif llm_menu.get() == "讯飞星火Lite":
            client = OpenAI(base_url=xf_url, api_key=xf_key)
            openai_history.append({"role": "user", "content": msg})
            messages = [{"role": "system", "content": prompt1}]
            messages.extend(openai_history)
            completion = client.chat.completions.create(model=xf_model, messages=messages)
            openai_history.append({"role": "assistant", "content": completion.choices[0].message.content})
            return completion.choices[0].message.content
        elif llm_menu.get() == "本地Transformers":
            try:
                client = OpenAI(base_url=f"http://{local_llm_ip}:{tf_port}/v1", api_key="transformers")
                openai_history.append({"role": "user", "content": msg})
                messages = [{"role": "system", "content": prompt1}]
                messages.extend(openai_history)
                completion = client.chat.completions.create(model=tf_model, messages=messages, stream=False)
                chunks = re.findall(r'^data:\s*(.+)$', completion, flags=re.MULTILINE)
                result_content = []
                for chunk in chunks:
                    try:
                        data = json.loads(chunk)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content is not None:
                            result_content.append(content)
                    except json.JSONDecodeError:
                        continue
                result_content = "".join(result_content).replace("\n", "")
                openai_history.append({"role": "assistant", "content": result_content})
                res = result_content
                if think_filter_switch == "on":
                    res = res.split("</think>")[-1].strip()
                return res
            except Exception as e:
                return f"本地Transformers服务未开启，错误详情：{e}"
        elif llm_menu.get() == "本地LM Studio":
            try:
                client = OpenAI(base_url=f"http://{local_llm_ip}:{lmstudio_port}/v1", api_key="lm-studio")
                openai_history.append({"role": "user", "content": msg})
                messages = [{"role": "system", "content": prompt1}]
                messages.extend(openai_history)
                completion = client.chat.completions.create(model="", messages=messages)
                openai_history.append({"role": "assistant", "content": completion.choices[0].message.content})
```

### Agent diagnosis

client.chat.completions.create with messages= The code snippet shows a language model call using OpenAI's chat completions API. It includes complex parsing logic, such as regex cleanup and try/except blocks around json.loads, which indicates pain in handling the structured output from the LLM. BAML would remove this need for retry loops and validation by providing a more robust and reliable way to handle the structured output.

### Illustrative BAML-style rewrite

```
// Define the typed result as a BAML class
class StepResult {
  title string
  content string
  next_action "continue" | "final_answer"
}

// Define a BAML function with a client and a prompt
function GenerateStep(user_input: string) -> StepResult {
  client "openai/gpt-4o-mini"
  prompt #"
    You are an assistant that reasons step by step.
    Return the title, content, and next action.

    {{ user_input }}

    {{ ctx.output_format }}
  "#
}
```

**Client usage:**

```
result = GenerateStep(user_input)
title = result.title
content = result.content
next_action = result.next_action
```

_Limits:_ This BAML rewrite assumes that the model will always return a valid JSON object with the expected fields. It also does not handle different models or base URLs, which are hardcoded in the original code.

### Outreach draft (for human review)

> This looked like an area where BAML could help simplify things. By automatically parsing and validating the structured output, you can eliminate manual parsing, try/except blocks, and regex cleanup. It would ensure that the output is correctly formatted and ready for use without additional code. What do you think about giving it a try?

_Tone check:_ helpful


---

## Example 3: cursor/eval

- **Source file:** https://github.com/cursor/eval/blob/20f1ae654a1a75d7c55f324f8b5b6a7f88b34953/run.py
- **Language:** Python
- **Pain type:** retry_logic  |  **Use case:** chatbot
- **Pain score:** 5/5  |  **Confidence:** 1.0  |  **Lead score:** 4.35
- **Why BAML may help:** BAML would help by automating the retry logic, exception handling, and validation of the LLM output. It could also provide more sophisticated error detection and recovery mechanisms, reducing the need for manual intervention and improving the reliability of the structured data generated by the language model.

### Original brittle code

```
azure_prompt,
    claude_prompt
)
from claude import claude_complete

load_dotenv()

HEADERS = {
    "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
    "Content-Type": "application/json",
}

HUMAN_EVAL = os.environ['PWD'] + '/data/HumanEval.jsonl'
OUT_FILE = os.environ['PWD'] + '/results/results-{}-{}.jsonl'

async def retry(sem, fn):
    for i in range(1, 3):
        try:
            async with sem:
                return await fn()
        except Exception as e:
            print(e)
            print('retrying')
            time.sleep(0.3*i)

    return await fn()

async def get_completion(sem, prompt, num_tries=1, model='code-davinci-002', num_errors=0):
    #print(num_tries)
    if num_tries == 1:
        temperature = 0.0
    elif num_tries == 10:
        temperature = 0.6
    elif num_tries == 100:
        temperature = 0.8
    else:
        raise ValueError("num_tries must be 1, 10, or 100")


    if model in {'gpt-3.5-turbo', 'gpt-4'}:
        completion = await retry(sem, lambda: openai.ChatCompletion.acreate(messages=prompt, model=model, temperature=temperature, max_tokens=1000, n=num_tries))
```

### Agent diagnosis

The snippet includes an explicit call to the OpenAI API using `openai.ChatCompletion.acreate(messages=prompt, model=model, temperature=temperature, max_tokens=1000, n=num_tries)`. The code demonstrates a clear pattern of retry logic around this LLM call. Specifically, it attempts to handle exceptions and retries up to 3 times with increasing sleep intervals. This type of brittleness is common when dealing with unreliable structured outputs from language models, as the model's response might occasionally be malformed or incomplete.

### Illustrative BAML-style rewrite

```
// Define the typed result as a BAML class
class CompletionResult {
  title string
  content string
  next_action "continue" | "final_answer"
}

// Define a BAML function with a client and a prompt
function GetCompletion(user_input: string, model: string) -> CompletionResult {
  client "openai/gpt-4o-mini"
  prompt #"
    You are an assistant that reasons step by step.
    Return the title, content, and next action.

    {{ user_input }}

    {{ ctx.output_format }}
  "#
}
```

**Client usage:**

```
result = b.GetCompletion(user_input, 'code-davinci-002')
print(result.title)
print(result.content)
```

_Limits:_ This BAML rewrite assumes that the model will return a structured response in the expected format. It does not handle different models or additional parameters that may be required for certain models.

### Outreach draft (for human review)

> This looked like an opportunity to simplify your retry logic and error handling. By using BAML, you could automate these processes, making your code cleaner and more reliable. I think it would be worth exploring how BAML could help streamline your workflow.

_Tone check:_ helpful
