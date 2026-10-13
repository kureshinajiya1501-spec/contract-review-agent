import os
from langchain_ollama import ChatOllama
from dotenv import load_dotenv

load_dotenv()

# llama3.2:3b supports tool calling and is much more reliable than qwen3:0.6b.
# Change the model with the OLLAMA_MODEL variable in your .env file.
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def create_llm():
    return ChatOllama(model=MODEL_NAME, temperature=0, num_predict=1024)


if __name__ == "__main__":
    llm = create_llm()
    print(llm.invoke("Say hello in one sentence.").content)
