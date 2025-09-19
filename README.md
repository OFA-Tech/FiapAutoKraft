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
