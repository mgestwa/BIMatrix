from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import logging
import os
from ragsk import process_json_data  # Import the processing function

load_dotenv()

app = Flask(__name__)
CORS(app)

# Remove all Semantic Kernel related code since we won't be using it

@app.route('/api/simplify', methods=['POST'])
def simplify_data():
    try:
        data = request.json
        logging.info(f"Received data type: {type(data)}")
        logging.info(f"Received data structure: {data.keys() if isinstance(data, dict) else 'not a dict'}")
        logging.debug(f"Dane wejściowe do uproszczenia: {data}")
        
        # Use ragsk.py function to simplify the data
        simplified_data = process_json_data(data)
        
        logging.info(f"Simplified data type: {type(simplified_data)}")
        logging.debug(f"Wynik uproszczenia: {simplified_data}")
        
        return jsonify({
            "status": "success",
            "simplified_data": simplified_data
        })
    
    except Exception as e:
        logging.error(f"Błąd podczas upraszczania danych: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)