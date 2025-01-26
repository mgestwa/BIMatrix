from flask import Flask, request, jsonify
from flask_cors import CORS
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions import KernelFunction, KernelArguments  # 👈 Nowe importy
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
    chat_service = OpenAIChatCompletion(
        service_id="chat",
        ai_model_id="gpt-3.5-turbo",
        api_key=api_key
    )
    kernel.add_service(chat_service)
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

        prompt = """
        [Jako ekspert BIM, przeanalizuj te elementy IFC:]
        {{$input}}
        Podsumowanie:
        - Liczba elementów: 
        - Typy: 
        """

        # 🔥 Nowe API do tworzenia funkcji
        function: KernelFunction = kernel.create_function_from_prompt(
            plugin_name="BIMAnalysis",
            function_name="AnalyzeIFC",
            prompt=prompt
        )

        arguments = KernelArguments(input=json.dumps(data, indent=2))
        analysis = run_async(kernel.invoke(function, arguments))

        return jsonify({
            "status": "success",
            "analysis": str(analysis)
        })

    except Exception as e:
        logging.error(f"💥 Błąd: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)