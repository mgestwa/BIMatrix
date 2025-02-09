from typing import Dict, List, Union, Any
import json
import os
import asyncio

# -------------------------------
# Część 1. Przetwarzanie danych JSON
# -------------------------------

DESIRED_KEYS = {
    "Name", "Class", "GlobalId", "Rodzina i typ",
    "Długość", "Szerokość", "Wielkość", "Wysokość", "Typ systemu"
}

PIPE_INDICATORS = {"Grubość ścianki", "Średnica wewnętrzna", "Średnica zewnętrzna"}

def is_pipe_element(node: Dict) -> bool:
    """Sprawdza, czy element jest rurowy na podstawie jego atrybutów."""
    return any(
        child.get("data", {}).get("Name", "").strip() in PIPE_INDICATORS
        for child in node.get("children", [])
    )

def clean_value(value: Any) -> str:
    """Czyści i formatuje wartość."""
    return value.strip() if isinstance(value, str) else str(value)

def process_dimensions(node: Dict, result: Dict) -> None:
    """Przetwarza wymiary elementu, uwzględniając specyfikę elementów rurowych."""
    is_pipe = is_pipe_element(node)
    
    dimension_mapping = {
        "Długość": "Długość",
        "Wielkość": "Wielkość",
        "Szerokość": "Szerokość",
        "Wysokość": "Wysokość"
    }

    for child in node.get("children", []):
        child_data = child.get("data", {})
        key = child_data.get("Name", "").strip()
        
        if key in dimension_mapping and key not in result:
            if is_pipe and key in ("Szerokość", "Wysokość"):
                result[key] = ""
            else:
                result[key] = clean_value(child_data.get("Value", ""))

    if is_pipe:
        result["Szerokość"] = result["Wysokość"] = ""

def process_node(node: Union[Dict, List], result: Dict) -> None:
    """Przetwarza węzeł drzewa JSON rekurencyjnie."""
    if isinstance(node, list):
        for item in node:
            process_node(item, result)
        return

    data = node.get("data", {})
    node_name = data.get("Name", "").strip()
    
    if node_name == "Wymiary":
        process_dimensions(node, result)
        return
        
    if node_name in DESIRED_KEYS and node_name not in result:
        if "Value" in data:
            result[node_name] = clean_value(data["Value"])
        elif node_name == "Name":
            result["Name"] = node_name

    for child in node.get("children", []):
        process_node(child, result)

def process_single_element(element: Dict) -> Dict:
    """Przetwarza pojedynczy element JSON."""
    result = {}
    process_node(element, result)
    return result

def process_json_data(json_data: Union[Dict, List]) -> Union[Dict, List[Dict]]:
    """Przetwarza dane JSON i zwraca przetworzone wyniki."""
    if isinstance(json_data, list):
        return [process_single_element(element) for element in json_data]
    return process_single_element(json_data)

# -------------------------------
# Część 2. Rozszerzenie: baza RAG z SemanticKernel
# -------------------------------

# Importujemy SemanticKernel oraz konfigurujemy usługi LLM
# Upewnij się, że masz zainstalowaną bibliotekę: pip install semantic-kernel
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,  
    OpenAIChatCompletion,
    OpenAITextEmbedding
)
from semantic_kernel.memory import VolatileMemoryStore
from semantic_kernel.memory.semantic_text_memory import SemanticTextMemory
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

execution_settings = OpenAIChatPromptExecutionSettings()
chat_history = ChatHistory()


def initialize_kernel():
    """
    Inicjalizuje jądro SemanticKernel, konfiguruje usługę text completions
    oraz embedding.
    """
    kernel = sk.Kernel()

    # Konfiguracja usługi embeddings
    embedding_service = OpenAITextEmbedding(
        ai_model_id="text-embedding-ada-002",
        api_key=api_key
    )
    kernel.add_service(embedding_service)

    # Konfiguracja usługi text completions
    chat_service = OpenAIChatCompletion(
        service_id="chat-gpt",
        ai_model_id="gpt-4",
        api_key=api_key
    )
    kernel.add_service(chat_service)

    # Inicjalizacja pamięci wektorowej z embeddings_generator
    memory_store = SemanticTextMemory(
        storage=VolatileMemoryStore(), 
        embeddings_generator=embedding_service
    )
    return kernel, memory_store

# Modify add_element_to_memory to async
async def add_element_to_memory(memory_store, element: Dict):
    """
    Dodaje przetworzony element IFC do pamięci wektorowej.
    """
    content = ", ".join(f"{k}: {v}" for k, v in element.items())
    record_id = element.get("GlobalId") or str(hash(content))
    description = f"Element IFC klasy {element.get('Class', 'Nieznana')}"

    await memory_store.save_information(
        collection="ifc_elements",
        text=content,
        id=record_id,
        description=description
    )
    print(f"📥 Dodano element {record_id[:8]}... do pamięci")

# Modify build_rag_database to async
async def build_rag_database(processed_data: Union[Dict, List[Dict]], memory_store):
    print("🏗️ Rozpoczynam budowanie bazy RAG...")
    if isinstance(processed_data, dict):
        await add_element_to_memory(memory_store, processed_data)
        print("✅ Dodano pojedynczy element do bazy")
    else:
        total = len(processed_data)
        for idx, element in enumerate(processed_data, 1):
            await add_element_to_memory(memory_store, element)
            print(f"📊 Postęp: {idx}/{total} elementów ({(idx/total)*100:.1f}%)")
    print("🎉 Zakończono budowanie bazy RAG!")

# Modify query_ifc_model to async
async def query_ifc_model(kernel, memory_store, query: str, top_k: int = 5):
    print(f"🔍 Przeszukuję bazę dla zapytania: '{query}'")
    search_results = await memory_store.search("ifc_elements", query, limit=top_k)
    print(f"📝 Znaleziono {len(search_results)} pasujących elementów")
    
    context = "\n".join(result.text for result in search_results)
    prompt = (
        f"Na podstawie poniższych danych o modelu IFC, odpowiedz na pytanie:\n\n"
        f"Kontekst:\n{context}\n\nPytanie: {query}\n\nOdpowiedź:"
    )
    
    print("🤖 Przygotowuję zapytanie do LLM...")
    chat_history = ChatHistory()
    chat_history.add_system_message("Jesteś asystentem pomagającym analizować modele IFC.")
    chat_history.add_user_message(prompt)
    
    print("⏳ Czekam na odpowiedź od LLM...")
    chat_service = kernel.get_service("chat-gpt")
    response = await chat_service.get_chat_message_content(
        chat_history=chat_history, 
        settings=execution_settings
    )
    print("✨ Otrzymano odpowiedź od LLM")
    return response.content

# Convert main to async function
async def main() -> None:
    print("🚀 Uruchamiam aplikację...")
    
    try:
        print("📂 Wczytuję plik data.json...")
        with open('data.json', 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        results = process_json_data(json_data)
        print("✅ Pomyślnie przetworzono dane IFC")
    except FileNotFoundError:
        print("❌ Błąd: Plik data.json nie został znaleziony!")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Błąd dekodowania JSON: {e}")
        return

    print("🔧 Inicjalizuję SemanticKernel...")
    kernel, memory_store = initialize_kernel()
    print("✅ Kernel i memory_store zainicjalizowane")

    await build_rag_database(results, memory_store)

    query = "Jaka jest długość elementu typu IFCFLOWSEGMENT?"
    print("\n💭 Przykładowe zapytanie:", query)
    answer = await query_ifc_model(kernel, memory_store, query)
    print("\n📢 Odpowiedź LLM:")
    print(f"🗨️ {answer}")
    print("\n✨ Zakończono działanie aplikacji")

if __name__ == "__main__":
    asyncio.run(main())