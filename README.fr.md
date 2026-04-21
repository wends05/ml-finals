# Final Project - Home Greeting System with Face Recognition

[English](README.md) | [中文](README.cn.md) | [Français](README.fr.md)

## Description

Un système d’accueil qui entraîne un modèle pour reconnaître des visages grâce à TensorFlow et Keras. Un contrôleur ESP32 est ensuite utilisé pour appeler un backend Python afin d’afficher, sur l’interface d’accueil, le nom du visage reconnu.

## Stack technique

- Python
- TensorFlow
- Keras
- ESP32
- FastAPI (backend)
- React (Vite) (frontend)

## Comment exécuter le projet

1. Commencez par cloner le dépôt et accéder au dossier du backend :

```bash
git clone
```

2. Installez les dépendances requises pour le backend :

```bash
cd backend
pip install -r requirements.txt
```

Vous pouvez aussi installer les dépendances avec le gestionnaire de paquets `uv` :

```bash
uv sync
```

3. Récupérez le jeu de données en suivant les instructions affichées lors de l’exécution de :

```bash
python backend/scripts/01a_collect_faces.py
```

Les données seront ensuite stockées dans le dossier `backend/dataset`, avec les données d’entraînement dans `backend/dataset/train` et les données de validation dans `backend/dataset/value`.

4. Entraînez le modèle à l’aide du script fourni. Vous pouvez utiliser n’importe quel modèle présent dans le dossier `backend/scripts/training`. Par exemple, pour entraîner le modèle avec l’ossature EfficientNetV2B0, exécutez :

```bash
python scripts/02_train_model_2.ipynb
```

Notez que pour `02_train_dense.ipynb`, vous devez disposer des fichiers `train_landmarks.csv` et `val_landmarks.csv` dans le dossier `backend/dataset`. Ils peuvent être générés en exécutant le script `01b_extract_landmarks.py`. Pour `02_train_model_1.ipynb` et `02_train_model_2.ipynb`, il n’est pas nécessaire de générer ces fichiers CSV des points d’ancrage, donc vous pouvez ignorer `01b_extract_landmarks.py` si vous souhaitez entraîner avec ces deux scripts.

5. Une fois l’entraînement terminé, le modèle sera enregistré dans le dossier `backend/models`. Vous pourrez ensuite démarrer le serveur backend avec uvicorn :

```bash
uvicorn main:app --reload
```

Vous pouvez changer le fichier keras utilisé (le modèle généré par le script d’entraînement) en modifiant la variable `MODEL_PATH` dans `backend/app/main.py`.

6. Enfin, démarrez le serveur frontend :

```bash
cd frontend
npm install
npm run dev
```

Vous pouvez également utiliser `bun` à la place de `npm` si vous l’avez installé :

```bash
cd frontend
bun install
bun run dev
```

7. Le frontend devrait maintenant être accessible à l’adresse `http://localhost:5173`. Vous pouvez tester la reconnaissance faciale en envoyant une requête POST au backend tout en montrant votre visage à la caméra via l’interface frontend. Si le visage est reconnu, le nom de la personne sera affiché sur l’interface d’accueil, et apparaîtra également dans le moniteur série de l’ESP32.

## Configuration ESP32 (Intégration Backend)

Ce projet inclut un firmware ESP32 dans `backend/esp32/` qui interroge des endpoints backend comme `/api/kiosk-status` et `/api/health`.

### 1. Installer Arduino IDE

- Téléchargez et installez Arduino IDE depuis le site officiel : https://www.arduino.cc/en/software

### 2. Configurer Arduino IDE pour ESP32

1. Ouvrez Arduino IDE.
2. Allez dans `File > Preferences`.
3. Dans `Additional boards manager URLs`, ajoutez :

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

4. Allez dans `Tools > Board > Boards Manager`.
5. Recherchez `esp32` et installez `esp32 by Espressif Systems`.
6. Connectez votre carte via USB-C.
7. Dans `Tools > Board`, sélectionnez `ESP32 Dev Module`.
8. Dans `Tools > Port`, sélectionnez le port COM de la carte.

Si l’upload échoue, vérifiez que le câble USB transporte les données (pas uniquement l’alimentation) et que la carte/port sélectionnés sont corrects.

### 3. Matériel nécessaire

- 2x LEDs
- 1x ESP32 WROOM 30 pin ism2.4c 302 USB-C
- 1x écran LCD I2C 16x2 avec backpack (5V)
- 1x capteur ultrason HC-SR04 (5V)
- 1x adaptateur USB-C vers USB-A (selon votre ESP32)

### 4. Note électrique importante (Pont diviseur)

La logique GPIO de l’ESP32 est en 3,3V. La broche Echo du HC-SR04 peut sortir du 5V.

Utilisez un pont diviseur entre `Echo HC-SR04` et la broche Echo de l’ESP32 pour ramener le signal vers 3,3V. Ne connectez pas directement Echo au GPIO de l’ESP32.

### 5. Configuration du firmware et des endpoints

1. Ouvrez `backend/esp32/kiosk_status_serial.ino` dans Arduino IDE.
2. Définissez :
	- `WIFI_SSID`
	- `WIFI_PASS`
	- `API_BASE_URL` (IP LAN de votre ordinateur et port backend, par exemple `http://<VOTRE_IP_LAN_PC>:3009`)
3. Téléversez sur l’ESP32.
4. Ouvrez le moniteur série à `115200` bauds.

### 6. Référence du pinout de la carte

![Référence Pinout ESP32](frontend/public/boardpinout.png)

## Spécifications

- Le modèle doit être entraîné sur un jeu de données de visages, avec au moins 5 classes différentes (personnes).
- Le modèle doit atteindre au moins 80 % de précision sur le jeu de validation.
- Le backend doit pouvoir recevoir une requête POST contenant une image et renvoyer la classe prédite (le nom de la personne) dans l’image.
- Le frontend doit pouvoir afficher le nom de la personne reconnue lorsqu’un visage est détecté par la caméra.
