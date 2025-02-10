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

# Initialize kernel and memory_store at module level
kernel, memory_store = initialize_kernel()
# Flag to track if RAG database is built
rag_database_built = False

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

@app.route('/api/build-rag', methods=['POST'])
def build_rag_handler():
    global rag_database_built
    try:
        data = request.json
        model_data = data.get('modelData')

        if not model_data:
            return jsonify({
                'status': 'error',
                'message': 'Missing model data'
            }), 400

        # Run async operations in a synchronous context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process the data and build RAG database
        simplified_data = process_json_data(model_data)
        loop.run_until_complete(build_rag_database(simplified_data, memory_store))
        loop.close()

        rag_database_built = True  # Set flag after successful build

        return jsonify({
            'status': 'success',
            'message': 'RAG database built successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/query', methods=['POST'])
def query_rag_handler():
    global rag_database_built
    try:
        if not rag_database_built:
            return jsonify({
                'status': 'error',
                'message': 'RAG database not built yet. Please build it first.'
            }), 400

        data = request.json
        query = data.get('query')

        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Missing query'
            }), 400

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
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