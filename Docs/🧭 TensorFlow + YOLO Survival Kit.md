## 📦 Instalação Essencial

```bash
pip install tensorflow opencv-python numpy
pip install ultralytics  # YOLOv8 (da Ultralytics)
```

> Verifique se está usando Python 3.8+ e uma versão do TensorFlow compatível com sua GPU (para CUDA/cuDNN).

---

## 🧠 YOLOv8 com Ultralytics (mais fácil e rápido)

### 🔍 Detecção com YOLOv8 pré-treinado

```python
from ultralytics import YOLO
import cv2

# Carregar modelo pré-treinado
model = YOLO('yolov8n.pt')  # Pode usar 'yolov8s.pt', 'yolov8m.pt', etc.

# Carregar imagem ou vídeo
img = cv2.imread('imagem.jpg')

# Rodar detecção
results = model(img)

# Mostrar resultados
results[0].plot()
cv2.imshow("Detecção", results[0].plot())
cv2.waitKey(0)
```

---

### 🏋️‍♂️ Treinamento personalizado com YOLOv8

1. Estrutura de diretório para dataset:
   ```
   dataset/
   ├── images/
   │   ├── train/
   │   └── val/
   └── labels/
       ├── train/
       └── val/
   ```

2. Exemplo de arquivo `data.yaml`:
   ```yaml
   path: ./dataset
   train: images/train
   val: images/val
   nc: 3
   names: ['caixa', 'garrafa', 'latinha']
   ```

3. Rodar treino:
   ```bash
   yolo task=detect mode=train model=yolov8n.yaml data=data.yaml epochs=50 imgsz=640
   ```

---

## 🧠 TensorFlow (para IA geral e customizações)

### 👁️‍🗨️ Pipeline de inferência com TensorFlow (CNNs, classificação, etc.)

```python
import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np
import cv2

# Carregar modelo
model = load_model('modelo.h5')

# Pré-processamento da imagem
img = cv2.imread('img.jpg')
img = cv2.resize(img, (224, 224)) / 255.0
img = np.expand_dims(img, axis=0)

# Previsão
pred = model.predict(img)
print("Classe:", np.argmax(pred))
```

---

### 💾 Salvando e carregando modelos

```python
# Salvar
model.save('modelo.h5')

# Carregar
model = tf.keras.models.load_model('modelo.h5')
```

---

## 🛠️ Ferramentas úteis

| Ferramenta           | Uso                                              |
|----------------------|--------------------------------------------------|
| Roboflow            | Anotação e geração de datasets (https://roboflow.com) |
| CVAT                | Anotação avançada local                           |
| Netron              | Visualização de modelos `.pt`, `.h5`, `.onnx`     |
| TensorBoard         | Monitorar treino do TensorFlow                    |
| OpenCV              | Leitura de câmera, transformação de imagem       |

---

## 📚 Cheatsheets

### Pré-processamento (YOLO-style):
```python
img = cv2.resize(img, (640, 640))
img = img / 255.0
img = img.transpose(2, 0, 1)  # Se necessário para PyTorch-style models
```

### Conversão de bounding box:
YOLO usa formato:  
```txt
<class_id> <x_center_norm> <y_center_norm> <width_norm> <height_norm>
```

Conversão de pixels para YOLO:
```python
def convert_to_yolo(x, y, w, h, img_w, img_h):
    return [
        (x + w/2) / img_w,
        (y + h/2) / img_h,
        w / img_w,
        h / img_h
    ]
```

---

## 🧪 Dicas Rápidas

- Use `yolov8n.pt` para velocidade, `yolov8s.pt` para melhor precisão.
- Para TensorFlow com GPU, certifique-se que CUDA está corretamente instalado.
- Para projetos com picking, combine YOLO para localização de objetos e TensorFlow para classificação fina ou decisão.
