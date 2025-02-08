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
let propertiesTable; // Zmienna globalna, aby uzyskać dostęp do tabeli właściwości
let loadedModel = null; // Globalna zmienna do przechowywania załadowanego modelu
let ifcManager = null; // Nowa zmienna do przechowywania referencji do ifcManager

// Funkcja do konfiguracji i wczytania pliku IFC oraz inicjalizacji tabeli właściwości
// Funkcja do wczytywania modelu IFC – modyfikujemy ją, aby zapisać model globalnie
async function loadIfcWithProperties(file) {
    await ifcLoader.setup();
    // Po setup, zapisz referencję do ifcManager
    ifcManager = ifcLoader.ifcManager;
  
    const container = document.getElementById("container");
    const worlds = components.get(OBC.Worlds);
    const world = worlds.create();
  
    world.scene = new OBC.SimpleScene(components);
    world.renderer = new OBC.SimpleRenderer(components, container);
    world.camera = new OBC.SimpleCamera(components);

    const viewerGrids = components.get(OBC.Grids);
    viewerGrids.create(world);
  
    components.init();
  
    world.camera.controls.setLookAt(12, 6, 8, 0, 0, -10);
    world.scene.setup();
  
    const highlighter = components.get(OBF.Highlighter);
    highlighter.setup({ world });

    // Wczytanie modelu
    const buffer = await file.arrayBuffer();
    const model = await ifcLoader.load(new Uint8Array(buffer));
    
    // Zapisujemy model globalnie
    loadedModel = model;
    
    // Dodaj model do sceny
    world.scene.three.add(model);

    // Inicjalizacja pozostałych komponentów (tabela właściwości, drzewo relacji itd.)
    await setupElementProperties(model, components, world);
    await setupRelationsTree(model, components, world);
    
    return model;
}


// Funkcja do inicjalizacji tabeli właściwości
async function setupElementProperties(model, components, world) {
    //const indexer = components.get(OBC.IfcRelationsIndexer);
    //await indexer.process(model);

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

async function setupRelationsTree(model, components, world) {
    const indexer = components.get(OBC.IfcRelationsIndexer);

    // Reset any existing data
    indexer.onFragmentsDisposed({ ids: Object.keys(indexer.relationMaps) });

    // Create relations tree before processing model
    const [relationsTree] = CUI.tables.relationsTree({
        components,
        models: [],
        rootName: "INP_ModelTest" // Dodaj nazwę root node'a
    });

    // Set up container
    const relationsContainer = document.getElementById("relations-tree-container");
    if (!relationsContainer) {
        console.warn('Nie znaleziono kontenera o id="relations-tree-container"');
        return;
    }
    relationsContainer.innerHTML = "";

    // Process model
    console.log("Processing model...");
    await indexer.process(model);
    console.log("Model processed");

    // Configure tree
    relationsTree.preserveStructureOnFilter = true;

    // Create controls container
    const controlsContainer = document.createElement("div");
    controlsContainer.style.display = "flex";
    controlsContainer.style.gap = "0.375rem";
    controlsContainer.style.marginBottom = "10px";

    // Add search input
    const searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search...";
    searchInput.style.flex = "1";
    searchInput.addEventListener("input", (event) => {
        relationsTree.queryString = event.target.value;
    });
    controlsContainer.appendChild(searchInput);

    // Add expand button
    const expandButton = document.createElement("button");
    expandButton.classList.add("expand-button");
    expandButton.addEventListener("click", () => {
        relationsTree.expanded = !relationsTree.expanded;
    });
    controlsContainer.appendChild(expandButton);

    // Add elements to container
    relationsContainer.appendChild(controlsContainer);
    relationsContainer.appendChild(relationsTree);

    // Setup highlighter
    try {
        const highlighter = components.get(OBF.Highlighter);
        relationsTree.addEventListener('click', (event) => {
            const row = event.target.closest('[data-id]');
            if (row) {
                const id = row.dataset.id;
                highlighter.highlight({ [id]: true });
                console.log("Selected element:", id);
            }
        });
    } catch (error) {
        console.error("Error in highlighter setup:", error);
    }

    return relationsTree;
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
    
    console.log("Dane z tabeli:", propertiesTable.data);
}

// Nowa funkcja do wysyłania danych przez API (do przetwarzania przez LLM i uproszczenia danych)
function sendDataForSimplification() {
    if (!propertiesTable || !propertiesTable.data) {
        alert("Tabela właściwości jest pusta!");
        return;
    }
    const jsonData = JSON.stringify(propertiesTable.data);
    fetch('http://localhost:5000/api/simplify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: jsonData,
    })
    .then(response => {
        if (!response.ok) throw new Error('Błąd odpowiedzi serwera przy uproszczeniu danych');
        return response.json();
    })
    .then(data => {
        console.log('Odpowiedź serwera (uproszczenie):', data);
        alert('Dane zostały pomyślnie wysłane do uproszczenia!');
    })
    .catch(error => {
        console.error('Błąd podczas wysyłania danych do uproszczenia:', error);
        alert('Wystąpił błąd: ' + error.message);
    });
    console.log("Dane z currentProperties:", currentProperties);
}
  
// Nowa funkcja do wysyłania danych przez API
function sendDataToApi() {
if (!propertiesTable || !propertiesTable.data) {
    alert("Tabela właściwości jest pusta!");
    return;
}
const jsonData = JSON.stringify(propertiesTable.data);
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
console.log("Dane z currentProperties:", currentProperties);
}


// Nowa funkcja do wysyłania danych wszystkich elementów do API w celu uproszczenia
async function sendAllElementsForSimplification() {
    let allProps = {};

    // Jeśli użytkownik zaznaczył jakieś elementy, używamy ich
    if (currentProperties && Object.keys(currentProperties).length > 0) {
        allProps = currentProperties;
    } else {
        // Jeśli currentProperties jest puste, spróbujmy pobrać WSZYSTKIE elementy z modelu IFC
        if (ifcManager) {
            const modelID = loadedModel.modelID;
            let allExpressIDs = [];
            try {
                allExpressIDs = await ifcManager.getAllItemsOfType(modelID, 0, false);
                console.log("Pobrano listę wszystkich elementów:", allExpressIDs);
            } catch (error) {
                console.error("Błąd pobierania listy elementów:", error);
                alert("Nie udało się pobrać listy elementów modelu! 😢");
                return;
            }
            
            // Pobieramy właściwości dla każdego elementu
            for (const expressID of allExpressIDs) {
                try {
                    const props = await loadedModel.getProperties(expressID);
                    allProps[expressID] = props;
                } catch (error) {
                    console.error(`Błąd pobierania właściwości dla elementu ${expressID}:`, error);
                }
            }
        } else {
            alert("Nie udało się pobrać ifcManager! Proszę zaznaczyć elementy ręcznie. 😢");
            return;
        }
    }

    if (Object.keys(allProps).length === 0) {
        alert("Brak właściwości elementów do wysłania! 😢");
        return;
    }

    const simplifiedResults = {};

    // Iterujemy po wszystkich elementach i wysyłamy je pojedynczo do API
    for (const [expressID, props] of Object.entries(allProps)) {
        const payload = JSON.stringify({ expressID, data: props });
        try {
            const response = await fetch('http://localhost:5000/api/simplify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
            });
            if (!response.ok) {
                throw new Error(`Błąd odpowiedzi serwera dla elementu ${expressID}`);
            }
            const result = await response.json();
            simplifiedResults[expressID] = result;
            console.log(`Uproszczone dane dla elementu ${expressID}:`, result);
        } catch (error) {
            console.error(`Błąd podczas wysyłania danych dla elementu ${expressID}:`, error);
        }
    }

    // Aktualizujemy dane w tabeli właściwości, aby funkcja downloadJson() pobrała właśnie te dane
    propertiesTable.data = simplifiedResults;

    // Wywołanie istniejącej funkcji do pobierania pliku JSON
    downloadJson();
    alert("Proces zakończony. Plik z uproszczonymi danymi został wygenerowany! 😊");
}


async function processElementsIndividuallyForSimplification() {
    // Sprawdzamy, czy model IFC został załadowany
    if (!loadedModel) {
        alert("Model IFC nie został załadowany! 😢");
        return;
    }
    // Sprawdzamy, czy ifcManager jest dostępny
    if (!ifcManager) {
        alert("ifcManager nie jest dostępny! Upewnij się, że model został poprawnie załadowany. 😢");
        return;
    }

    // Pobieramy identyfikator modelu (zakładamy, że loadedModel.modelID jest ustawiony)
    const modelID = loadedModel.modelID;
    let allExpressIDs = [];
    try {
        // Pobieramy listę wszystkich identyfikatorów elementów typu 0 (wszystkie elementy)
        allExpressIDs = await ifcManager.getAllItemsOfType(modelID, 0, false);
        console.log("Lista wszystkich elementów:", allExpressIDs);
    } catch (error) {
        console.error("Błąd pobierania listy elementów:", error);
        alert("Nie udało się pobrać listy elementów modelu! 😢");
        return;
    }
    
    const simplifiedResults = {};

    // Przetwarzamy element po elemencie
    for (const expressID of allExpressIDs) {
        try {
            // Pobieramy właściwości dla danego elementu
            const props = await loadedModel.getProperties(expressID);
            // Przygotowujemy payload dla API
            const payload = JSON.stringify({ expressID, data: props });
            // Wysyłamy dane do API do uproszczenia
            const response = await fetch('http://localhost:5000/api/simplify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
            });
            if (!response.ok) {
                console.error(`Błąd odpowiedzi serwera dla elementu ${expressID}`);
                continue;
            }
            const result = await response.json();
            simplifiedResults[expressID] = result;
            console.log(`Uproszczone dane dla elementu ${expressID}:`, result);
            // Opcjonalnie: dodajemy krótki delay (np. 100ms), aby nie przeciążać API
            await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
            console.error(`Błąd przetwarzania elementu ${expressID}:`, error);
        }
    }
    
    // Po zakończeniu przetwarzania ustawiamy uproszczone dane w tabeli właściwości
    propertiesTable.data = simplifiedResults;
    // Pobieramy plik JSON z uproszczonymi danymi (używamy istniejącej funkcji)
    downloadJson();
    alert("Proces zakończony! Plik z uproszczonymi danymi został wygenerowany! 😊");
}
  

// Przypisanie event listenerów do osobnych przycisków
document.getElementById("downloadJson").addEventListener("click", downloadJson);
document.getElementById("sendToApi").addEventListener("click", sendDataToApi);
document.getElementById("simplifyAllElements").addEventListener("click", processElementsIndividuallyForSimplification);

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