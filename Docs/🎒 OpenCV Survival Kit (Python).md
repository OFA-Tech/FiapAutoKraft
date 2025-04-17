## 📦 Instalação Essencial

```bash
pip install opencv-python opencv-python-headless numpy
```

> Use `opencv-python-headless` se estiver rodando em servidor ou container sem GUI.

---

## 📸 Leitura de Imagens e Vídeos

```python
import cv2

# Imagem
img = cv2.imread('imagem.jpg')
cv2.imshow('Imagem', img)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Webcam
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow('Webcam', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
```

---

## 🎯 Operações Essenciais

### 🔄 Resize, Crop, Rotate

```python
resized = cv2.resize(img, (640, 480))
cropped = img[100:300, 200:400]
rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
```

### 💡 Conversão de Cores

```python
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
```

### 🎨 Desenhar na Imagem

```python
cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), 2)
cv2.circle(img, (100, 100), 50, (255, 0, 0), 3)
cv2.putText(img, 'Objeto', (70, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
```

---

## 🧠 Detecção de Objetos e Formas

### 🎲 Detecção de Contornos

```python
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

for cnt in contours:
    area = cv2.contourArea(cnt)
    if area > 1000:
        cv2.drawContours(img, [cnt], -1, (0, 255, 0), 2)
```

### 🟩 Detecção de Cores (Ex: verde)

```python
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lower = (40, 40, 40)
upper = (70, 255, 255)
mask = cv2.inRange(hsv, lower, upper)
result = cv2.bitwise_and(img, img, mask=mask)
```

---

## 🧭 Visão Computacional para Robótica

### 🔍 Leitura de posição de objeto

```python
M = cv2.moments(cnt)
if M['m00'] != 0:
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    cv2.circle(img, (cx, cy), 5, (0, 0, 255), -1)
```

---

## 📐 Calibração e Medição

### 📏 Medir distância entre dois pontos

```python
import math
p1 = (100, 100)
p2 = (200, 200)
dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
```

---

## 🧪 Processamento de Imagem Avançado

### 🧹 Filtros

```python
blur = cv2.GaussianBlur(img, (5, 5), 0)
edges = cv2.Canny(img, 100, 200)
```

### 🧱 Transformações

```python
M = cv2.getRotationMatrix2D((img.shape[1]//2, img.shape[0]//2), 45, 1)
rotated = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
```

---

## ⚙️ Integrações úteis

| Componente            | Como usar com OpenCV                     |
|----------------------|-------------------------------------------|
| TensorFlow            | Enviar imagem tratada para rede neural  |
| YOLOv8                | Usar `results[0].plot()` do YOLO sobre frame do OpenCV |
| Arduinos / robôs      | Detectar objetos e enviar coordenadas via serial |
| ROS                   | Publicar imagem com `cv_bridge` |

---

## 📚 Cheatsheet Extra

### Detecção de movimento simples:

```python
ret, frame1 = cap.read()
ret, frame2 = cap.read()
diff = cv2.absdiff(frame1, frame2)
gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray, (5,5), 0)
_, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
```
