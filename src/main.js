// Aktualizacja main.js z dodaniem eksportu właściwości

// Importowanie niezbędnych modułów
import * as WEBIFC from "web-ifc";
import * as BUI from "@thatopen/ui";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";
import * as CUI from "@thatopen/ui-obc";

BUI.Manager.init();

// Inicjalizacja komponentów
const components = new OBC.Components();
const ifcLoader = components.get(OBC.IfcLoader);

let currentProperties = {}; // Zmienna globalna do przechowywania właściwości

// Funkcja do konfiguracji i wczytania pliku IFC oraz inicjalizacji tabeli właściwości
async function loadIfcWithProperties(file) {
    await ifcLoader.setup();

    // Tworzenie podstawowych komponentów (Scena, Renderer, Kamera)
    const container = document.getElementById("container");
    const worlds = components.get(OBC.Worlds);
    const world = worlds.create();

    world.scene = new OBC.SimpleScene(components);
    world.renderer = new OBC.SimpleRenderer(components, container);
    world.camera = new OBC.SimpleCamera(components);

    components.init();

    world.camera.controls.setLookAt(12, 6, 8, 0, 0, -10);
    world.scene.setup();

    // Odczytanie zawartości pliku IFC
    const buffer = await file.arrayBuffer();
    const uint8Array = new Uint8Array(buffer);

    // Wczytanie modelu IFC
    const model = await ifcLoader.load(uint8Array);

    // Dodanie modelu do sceny
    world.scene.three.add(model);

    // Konfiguracja tabeli właściwości elementów
    await setupElementProperties(model, components, world);
}

let propertiesTable; // Zmienna globalna, aby uzyskać dostęp do tabeli właściwości

// Funkcja do inicjalizacji tabeli właściwości
async function setupElementProperties(model, components, world) {
    const indexer = components.get(OBC.IfcRelationsIndexer);
    await indexer.process(model);

    const [tableComponent, updatePropertiesTable] = CUI.tables.elementProperties({
        components,
        fragmentIdMap: {},
    });

    // Assign to global propertiesTable
    propertiesTable = tableComponent;
    
    propertiesTable.preserveStructureOnFilter = true;
    propertiesTable.indentationInText = false;

    const propertyContainer = document.getElementById("properties");
    propertyContainer.innerHTML = ""; // Wyczyść kontener
    propertyContainer.appendChild(propertiesTable);

    console.log("Tabela właściwości elementów została utworzona.");

    // Inicjalizacja Highlightera
    const highlighter = components.get(OBF.Highlighter);
    highlighter.setup({ world });

    highlighter.events.select.onHighlight.add(async (fragmentIdMap) => {
        updatePropertiesTable({ fragmentIdMap });
    
        // Pobierz expressIDs z fragmentIdMap
        const expressIDs = [];
        for (const fragmentID in fragmentIdMap) {
            const ids = fragmentIdMap[fragmentID];
            expressIDs.push(...ids);
        }
    
        currentProperties = {}; // Reset current properties
    
        // Pobierz właściwości dla każdego expressID bezpośrednio z modelu
        for (const expressID of expressIDs) {
            try {
                const props = await model.getProperties(expressID); // Poprawione wywołanie
                currentProperties[expressID] = props;
            } catch (error) {
                console.error(`Błąd podczas pobierania właściwości dla ExpressID ${expressID}:`, error);
            }
        }
    
        console.log("Zaktualizowane właściwości:", currentProperties);
    });

    highlighter.events.select.onClear.add(() => {
        updatePropertiesTable({ fragmentIdMap: {} });
        currentProperties = {}; // Czyszczenie właściwości
    });

}

// Funkcja do pobierania JSON-a (istniejąca funkcjonalność)
function downloadJson() {
    if (propertiesTable) {
      propertiesTable.downloadData("selectedElementData.json", "json");
      console.log("Eksport danych do JSON z tabeli właściwości.");
    } else {
      alert("Tabela właściwości nie została zainicjalizowana.");
      console.error("Tabela właściwości jest niezainicjalizowana.");
    }
  }
  
// Nowa funkcja do wysyłania danych przez API
function sendDataToApi() {
if (Object.keys(currentProperties).length === 0) {
    console.log("Brak danych do wysłania.");
    alert("Najpierw wybierz element z właściwościami!");
    return;
}

const jsonData = JSON.stringify(currentProperties);
fetch('http://localhost:5000/api/data', {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json',
    },
    body: jsonData,
})
.then(response => {
    if (!response.ok) throw new Error('Błąd odpowiedzi serwera');
    return response.json();
})
.then(data => {
    console.log('Odpowiedź serwera:', data);
    alert('Dane zostały pomyślnie wysłane!');
})
.catch(error => {
    console.error('Błąd podczas wysyłania danych:', error);
    alert('Wystąpił błąd: ' + error.message);
});
}

// Przypisanie event listenerów do osobnych przycisków
document.getElementById("downloadJson").addEventListener("click", downloadJson);
document.getElementById("sendToApi").addEventListener("click", sendDataToApi);

// Obsługa zdarzenia wyboru pliku z obsługą tabeli właściwości
document.getElementById("ifcFile").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
            await loadIfcWithProperties(file);
        } catch (error) {
            console.error("Błąd podczas wczytywania pliku IFC:", error);
        }
    } else {
        console.error("Nie wybrano pliku.");
    }
});
