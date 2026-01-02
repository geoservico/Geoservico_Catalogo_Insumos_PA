# Geoservico - Subscription Input Catalog (PA)

## Overview

The **Geoservico - Subscription Input Catalog (PA)** is a QGIS plugin developed for Geoserviço - Geotecnologia & Meio. Its primary function is to provide authenticated access to a catalog of WMS (Web Map Service) layers that are part of a subscription service.

This plugin streamlines the process of connecting to the Geoserviço WMS server, handling user authentication securely, and presenting a filtered list of available layers for the user's subscription.

## Features

*   **Secure Authentication:** Handles user login and stores credentials securely using QGIS settings.
*   **WMS Layer Catalog:** Fetches and displays a list of available WMS layers from the Geoserviço server.
*   **Layer Filtering:** Allows users to search and filter the layer list.
*   **Background Loading:** Loads selected WMS layers into the QGIS project in a separate thread to maintain application responsiveness.

## Requirements and Dependencies

### QGIS Version

This plugin requires **QGIS version 3.40** or later.

### External Python Dependencies

The plugin relies on the standard QGIS Python environment but has one external dependency:

*   **`requests`**: Used for secure HTTP communication, particularly for user authentication and fetching the WMS capabilities document.

#### Installation of `requests`

While `requests` is a common library, it may not be available in all QGIS installations, especially on Windows.

**For Windows Users (OSGeo4W Shell):**

1.  Open the **OSGeo4W Shell** (Start Menu -> OSGeo4W -> OSGeo4W Shell).
2.  Execute the following command to install the library into the QGIS Python environment:
    ```bash
    pip install requests
    ```
    *If you encounter permission issues, you may need to run the shell as an administrator.*

**For Linux/macOS Users:**

The `requests` library is typically available by default or easily installed via your system's package manager or `pip` if needed.

## Installation

1.  Download the plugin ZIP file.
2.  In QGIS, go to **Plugins** -> **Manage and Install Plugins...**
3.  Go to the **Install from ZIP** tab.
4.  Select the downloaded ZIP file and click **Install Plugin**.
5.  The plugin will appear under the **Web** menu as **Geoserviço - Catálogo de Insumos por Assinatura-PA**.

## Usage

1.  Go to **Web** -> **Geoserviço - Catálogo de Insumos por Assinatura-PA**.
2.  A login dialog will appear. Enter your **Geoserviço** subscription credentials.
3.  Upon successful login, a list of available WMS layers will be displayed.
4.  Select the desired layers and click **Carregar Selecionadas** (Load Selected).
5.  The layers will be added to your QGIS project.

## License

This plugin is licensed under the **GNU General Public License, Version 2 or later (GPLv2+)**. See the `LICENSE` file for full details.

## Source Code and Issue Tracker

*   **Code Repository:** [https://github.com/yourusername/Geoservico_Catalogo_Insumos_PA](https://github.com/yourusername/Geoservico_Catalogo_Insumos_PA)
*   **Issue Tracker:** [https://github.com/yourusername/Geoservico_Catalogo_Insumos_PA/issues](https://github.com/yourusername/Geoservico_Catalogo_Insumos_PA/issues)
*   **Homepage:** [https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/](https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/) (Placeholder for dependency guide)

***
**Note:** Please replace `https://github.com/yourusername/Geoservico_Catalogo_Insumos_PA` with the actual repository URL before publication. The homepage link is a placeholder example provided in the requirements for external dependency installation guides.
