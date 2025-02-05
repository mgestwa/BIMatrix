from flask import Flask, request, jsonify
from flask_cors import CORS
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable
from semantic_kernel.functions import KernelArguments, KernelFunction, KernelPlugin
from dotenv import load_dotenv
import asyncio
import json
import logging
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

# Konfiguracja Semantic Kernel
kernel = Kernel()
api_key = os.getenv("OPENAI_API_KEY")

try:
    service = OpenAIChatCompletion(
        service_id="chat-gpt",
        ai_model_id="gpt-4o",  # Upewnij się, że model jest odpowiedni dla Twojego zastosowania
        api_key=api_key
    )
    kernel.add_service(service)
    logging.info("✅ Usługa OpenAI skonfigurowana!")
except Exception as e:
    logging.error(f"❌ Błąd: {str(e)}")
    exit(1)

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.route('/api/data', methods=['POST'])
def analyze_data():
    try:
        data = request.json
        logging.debug(f"Dane wejściowe: {json.dumps(data, indent=2)}")
        
        # Nowy prompt, który:
        # Krok 1: Upraszcza dane każdego elementu, wyodrębniając kluczowe właściwości (np. Nazwa, Typ, Wymiary, Materiał).
        # Krok 2: Na podstawie upraszczania generuje zestawienie ilościowe – liczbę elementów, główne typy, podsumowanie rozmiarów i materiałów.
        prompt_template_config = PromptTemplateConfig(
            template="""
[Jako ekspert BIM, przeanalizuj poniższe dane elementów IFC.]

Krok 1: Uprość dane wejściowe – dla każdego elementu wyodrębnij kluczowe właściwości, takie jak:
  - Nazwa elementu
  - Typ (np. IFCFLOWSEGMENT, itp.)
  - Rodzina i typ
  - Wymiary (np. wielkość, średnica)
  - Materiał

Krok 2: Na podstawie uproszczonych danych stwórz zestawienie ilościowe, zawierające:
  - Całkowitą liczbę elementów
  - Główne typy elementów wraz z ich ilością
  - Podsumowanie rozmiarów (np. średnia wielkość lub zakres wymiarów)
  - Rozkład materiałów

Dane wejściowe:
{{$input}}

Odpowiedz w formacie JSON.
            """,
            input_variables=[
                InputVariable(name="input", description="Dane IFC", is_required=True)
            ]
        )

        # Utworzenie funkcji na podstawie promptu
        analyze_function = KernelFunction.from_prompt(
            function_name="AnalyzeMultipleIFCElements",
            plugin_name="BIMAnalysis",
            prompt_template_config=prompt_template_config
        )

        # Utworzenie pluginu i dodanie do kernela
        plugin = KernelPlugin(name="BIMAnalysis", functions=[analyze_function])
        kernel.add_plugin(plugin)

        # Przygotowanie argumentów – dane wejściowe (mogą to być np. lista elementów lub obiekt zawierający wiele elementów)
        arguments = KernelArguments(input=json.dumps(data, indent=2))

        # Wywołanie funkcji asynchronicznie
        analysis = run_async(
            kernel.invoke(function=analyze_function, arguments=arguments)
        )

        return jsonify({
            "status": "success",
            "analysis": str(analysis)
        })

    except Exception as e:
        logging.error(f"💥 Błąd: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
