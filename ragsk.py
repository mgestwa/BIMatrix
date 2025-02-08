from typing import Dict, List, Union, Any
import json

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

def process_json_data(json_data: Union[Dict, List]) -> Union[Dict, List[Dict]]:
    """Przetwarza dane JSON i zwraca przetworzone wyniki."""
    if isinstance(json_data, list):
        return [process_single_element(element) for element in json_data]
    return process_single_element(json_data)

def process_single_element(element: Dict) -> Dict:
    """Przetwarza pojedynczy element JSON."""
    result = {}
    process_node(element, result)
    return result

def main() -> None:
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        results = process_json_data(json_data)
        print(json.dumps(results, indent=4, ensure_ascii=False))
        
    except FileNotFoundError:
        print("Plik data.json nie został znaleziony.")
    except json.JSONDecodeError as e:
        print(f"Błąd dekodowania JSON: {e}")

if __name__ == "__main__":
    main()