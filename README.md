# 📦 AutoKraft – Challenge FIAP 2025
Repositório oficial do grupo AutoKraft para o Challenge FIAP 2025, um projeto interdisciplinar que une engenharia de computação, visão computacional, robótica autônoma, machine learning e inteligência artificial.

# Nosso objetivo é desenvolver um sistema robótico inteligente, capaz de navegar autonomamente, identificar objetos via IA e realizar picking logístico com alta precisão em um ambiente de estoque simulado, utilizando tecnologias de ponta da Indústria 4.0.

💡 Visão Geral do Projeto
🚗 Plataforma móvel autônoma (AMR): simulação baseada no robô MiR 100

🤖 Braço robótico colaborativo: simulação do UR3e para coleta de objetos

🎯 Desafios:

Navegação autônoma e mapeamento do ambiente (SLAM)

Reconhecimento de produtos com Deep Learning (ex: YOLO, CNNs)

Execução precisa do processo de picking

Comunicação com o usuário (feedback visual e/ou interface)

# 🧠 IA embarcada: decisões em tempo real para planejamento de trajeto, reconhecimento e manipulação

# 🔧 Tecnologias Sugeridas
Visão Computacional: OpenCV, YOLOv5/v8, TensorFlow, PyTorch

Controle e navegação: ROS (Robot Operating System), SLAM

Hardware (simulado): MiR 100, UR3e, NVIDIA Jetson, câmeras ZED

Integração de sistemas: Python, C++, Docker, MQTT, REST APIs

## 🖥️ Ferramentas adicionais

- **Console-ComputationalVision** – Aplicativo em Python para executar as mesmas
  detecções YOLO do serviço de API diretamente no console. Permite testar
  imagens, vídeos ou câmeras ao vivo desenhando as bounding boxes e exibindo a
  posição `(x, y)` dos objetos detectados. O script agora aceita parâmetros de
  linha de comando para configurar o modelo YOLOv12, escolher a câmera, ajustar
  resolução e aplicar *digital zoom* (por exemplo `--digital-zoom 0.7` para
  "afastar" a visualização mantendo a inferência na imagem original).

### ▶️ Como executar o Console-ComputationalVision

1. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```
2. Instale as dependências do módulo:
   ```bash
   pip install -r Console-ComputationalVision/requirements.txt
   ```
3. Garanta que o diretório `Console-ComputationalVision/models` contenha o
   modelo YOLO a ser utilizado (por padrão, `models/best.pt`).
4. No terminal, defina o diretório de trabalho como `Console-ComputationalVision`
   e execute o aplicativo principal:
   ```bash
   cd Console-ComputationalVision
   python main.py
   ```
   O script `main.py` instancia a GUI Tkinter definida em
   `presentation/gui_app.py` e aceita argumentos de linha de comando como
   `--model-path`, `--camera-index` e `--frame-width` para ajustar a execução de
   acordo com o hardware disponível. Consulte `infrastructure/config_loader.py`
   para ver a lista completa de opções.

Se ocorrer um erro de importação relacionado ao OpenCV (por exemplo,
`ImportError: libGL.so.1`), instale as bibliotecas de sistema necessárias para o
OpenCV na sua plataforma ou utilize a distribuição `opencv-python-headless`.
