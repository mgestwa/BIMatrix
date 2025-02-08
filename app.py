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
        ai_model_id="gpt-4o",  # Upewnij się, że używasz właściwego modelu
        api_key=api_key
    )
    kernel.add_service(service)
    logging.info("✅ Usługa OpenAI skonfigurowana!")
except Exception as e:
    logging.error(f"❌ Błąd konfiguracji usługi OpenAI: {str(e)}")
    exit(1)

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.route('/api/simplify', methods=['POST'])
def simplify_data():
    try:
        data = request.json
        logging.debug(f"Dane wejściowe do uproszczenia: {json.dumps(data, indent=2)}")
        
        # Konfiguracja promptu do uproszczenia danych
        simplify_prompt_config = PromptTemplateConfig(
            template="""
[Jako ekspert BIM, uprość dane elementów IFC.]

Dla każdego elementu z poniższych danych wyodrębnij kluczowe właściwości:
  - Nazwa elementu
  - Typ (np. IFCFLOWSEGMENT, itp.)
  - Rodzina i typ
  - Wymiary (np. wielkość, średnica)
  - Materiał

Dane wejściowe:
{{$input}}

Odpowiedz w formacie JSON, zawierając uproszczone dane dla każdego elementu.
            """,
            input_variables=[
                InputVariable(name="input", description="Dane IFC", is_required=True)
            ]
        )
        
        # Utworzenie funkcji upraszczającej
        simplify_function = KernelFunction.from_prompt(
            function_name="SimplifyIFCData",
            plugin_name="BIMSimplification",
            prompt_template_config=simplify_prompt_config
        )
        
        # Utworzenie pluginu i dodanie do kernela
        plugin_simplify = KernelPlugin(name="BIMSimplification", functions=[simplify_function])
        kernel.add_plugin(plugin_simplify)
        
        # Przygotowanie argumentów – przekazujemy dane wejściowe w formacie JSON
        arguments_simplify = KernelArguments(input=json.dumps(data, indent=2))
        
        # Wywołanie funkcji asynchronicznie
        simplified_result = run_async(
            kernel.invoke(function=simplify_function, arguments=arguments_simplify)
        )
        
        # Jeśli wynik posiada atrybut `result`, używamy go; w przeciwnym razie konwertujemy cały wynik do stringa.
        result_text = getattr(simplified_result, "result", str(simplified_result))
        logging.debug(f"Wynik uproszczenia: {result_text}")
        
        return jsonify({
            "status": "success",
            "simplified_data": result_text
        })
    
    except Exception as e:
        logging.error(f"Błąd podczas uproszczania danych: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
