import torch
import cv2
from ultralytics import YOLO
import cvzone

def draw_bounding_boxes(frame, results, names):
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0]
            cls = int(box.cls[0])
            label = names[cls]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cvzone.putTextRect(frame, f'{label} {conf:.2f}', (x1, y1 - 10), scale=1, thickness=1, offset=3)
    return frame

def process_frame(frame, model, names):
    results = model(frame)[0]
    frame = draw_bounding_boxes(frame, results, names)
    return frame

def main():
    model: YOLO = YOLO('models/coke_latest.pt')
    names = model.names

    cap = cv2.VideoCapture(1)
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % 3 == 0:
            frame = process_frame(frame, model, names)

        cv2.imshow('YOLOv8 Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break



if __name__ == '__main__':
    print(f'Cuda Available: {torch.cuda.is_available()}')
    print(f'Cuda Version: {torch.version.cuda}')
    print(f'Cuda Device: {torch.cuda.get_device_name(0)}')
    raise SystemExit(main())