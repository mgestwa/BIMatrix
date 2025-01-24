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

    // Obsługa zdarzeń podświetlania
    highlighter.events.select.onHighlight.add((fragmentIdMap) => {
        updatePropertiesTable({ fragmentIdMap });
        //currentProperties = propertiesTable.downloadData("test.json", "json"); // Przechowuj właściwości w zmiennej
    });

    highlighter.events.select.onClear.add(() => {
        updatePropertiesTable({ fragmentIdMap: {} });
        currentProperties = {}; // Czyszczenie właściwości
    });
}

// Funkcja do eksportowania danych do JSON
function exportPropertiesToJson() {
    if (propertiesTable) {
        propertiesTable.downloadData("selectedElementData.json", "json");
        console.log("Eksport danych do JSON z tabeli właściwości.");
    } else {
        alert("Tabela właściwości nie została zainicjalizowana.");
        console.error("Tabela właściwości jest niezainicjalizowana.");
    }
}

// Przypisanie event listener do przycisku
document.getElementById("downloadJson").addEventListener("click", exportPropertiesToJson);

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
