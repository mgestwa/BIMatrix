from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from ragsk2 import (
    process_json_data,
    initialize_kernel,
    build_rag_database,
    query_ifc_model
)

app = Flask(__name__)
# Configure CORS properly
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Global variables for kernel and memory store
kernel = None
memory_store = None

# Initialize before first request instead of every request
@app.before_request
def initialize():
    global kernel, memory_store
    kernel, memory_store = initialize_kernel()

@app.route('/api/simplify', methods=['POST'])
def simplify_data():
    try:
        data = request.json
        simplified_data = process_json_data(data)
        return jsonify({
            'status': 'success',
            'simplified_data': simplified_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/query', methods=['POST'])
def query_rag_handler():
    try:
        data = request.json
        query = data.get('query')
        model_data = data.get('modelData')

        if not query or not model_data:
            return jsonify({
                'status': 'error',
                'message': 'Missing query or model data'
            }), 400

        # Run async operations in a synchronous context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process the data and build RAG database
        simplified_data = process_json_data(model_data)
        loop.run_until_complete(build_rag_database(simplified_data, memory_store))

        # Query the RAG database
        answer = loop.run_until_complete(query_ifc_model(kernel, memory_store, query))
        loop.close()

        return jsonify({
            'status': 'success',
            'answer': answer
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)