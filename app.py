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
        ai_model_id="gpt-4o",
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
        logging.debug(f"Dane: {json.dumps(data, indent=2)}")

        # Konfiguracja promptu
        prompt_template_config = PromptTemplateConfig(
            template="""
            [Jako ekspert BIM, przeanalizuj te elementy IFC:]
            {{$input}}
            
            Podsumowanie:
            - Liczba elementów: 
            - Główne typy: 
            - Wielkość lub średnica: 
            - Materiał: 
            """,
            input_variables=[
                InputVariable(name="input", description="Dane IFC", is_required=True)
            ]
        )

        # Utwórz funkcję z promptu
        analyze_function = KernelFunction.from_prompt(
            function_name="AnalyzeIFC",
            plugin_name="BIMAnalysis",
            prompt_template_config=prompt_template_config
        )

        # Stwórz plugin i dodaj do kernela
        plugin = KernelPlugin(name="BIMAnalysis", functions=[analyze_function])
        kernel.add_plugin(plugin)

        # Przygotuj argumenty
        arguments = KernelArguments(input=json.dumps(data, indent=2))

        # Wywołaj funkcję
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