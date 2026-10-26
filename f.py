import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import os

try:
    import easyocr
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

reader = None

try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

W, H = 1280, 720

BRUSH_SIZE = 7
ERASER_SIZE = 35


PANEL_H = 150

COLORS = [
    (0, 0, 255),     
    (0, 255, 0),       
    (255, 0, 0),       
    (0, 255, 255)      
]

COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]

color_index = 0

canvas = np.zeros((H, W, 3), dtype=np.uint8)

previous_x = 0
previous_y = 0

voice_command = ""
voice_status = "VOICE: READY"

recognition_text = (
    "AI: PRESS R TO RECOGNIZE"
    if AI_AVAILABLE
    else "AI: INSTALL EASYOCR"
)

assistant_message = "Draw something!"

voice_running = False
recognition_running = False

canvas_lock = threading.Lock()
state_lock = threading.Lock()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.65,
    min_tracking_confidence=0.65
)

def listen_voice():
    global voice_command, voice_status, voice_running

    try:
        if not VOICE_AVAILABLE:
            voice_status = "VOICE: INSTALL REQUIRED LIBRARIES"
            return

        recognizer = sr.Recognizer()

        with sr.Microphone() as source:

            voice_status = "VOICE: LISTENING..."

            recognizer.adjust_for_ambient_noise(
                source, duration=0.5
            )

            audio = recognizer.listen(
                source,
                timeout=4,
                phrase_time_limit=4
            )

        command = recognizer.recognize_google(
            audio,
            language="en-US"
        ).lower()

        with state_lock:
            voice_command = command
            voice_status = "HEARD: " + command[:35]

    except Exception as error:
        voice_status = "VOICE: NOT RECOGNIZED"
        print("Voice error:", error)

    finally:
        voice_running = False


def start_voice():
    global voice_running

    if not VOICE_AVAILABLE:
        print("Install SpeechRecognition and PyAudio")
        return

    if not voice_running:
        voice_running = True

        threading.Thread(
            target=listen_voice,
            daemon=True
        ).start()



def recognize_handwriting():
    global reader
    global recognition_text
    global recognition_running
    global assistant_message

    try:
        if not AI_AVAILABLE:
            recognition_text = "AI: INSTALL EASYOCR"
            return

        recognition_text = "AI: PROCESSING..."

        with canvas_lock:
            image_canvas = canvas.copy()

        gray = cv2.cvtColor(
            image_canvas,
            cv2.COLOR_BGR2GRAY
        )

        _, mask = cv2.threshold(
            gray, 1, 255, cv2.THRESH_BINARY
        )

        coords = cv2.findNonZero(mask)

        if coords is None:
            recognition_text = "AI: CANVAS IS EMPTY"
            assistant_message = "Write something first."
            return

        x, y, w, h = cv2.boundingRect(coords)

       
        cropped = gray[
            max(0, y - 20):min(H, y + h + 20),
            max(0, x - 20):min(W, x + w + 20)
        ]

       
        image = 255 - cropped

        image = cv2.resize(
            image,
            None,
            fx=1.5,
            fy=1.5,
            interpolation=cv2.INTER_CUBIC
        )

        if reader is None:
            recognition_text = "AI: LOADING MODEL..."

            reader = easyocr.Reader(
                ["en"],
                gpu=False
            )

        results = reader.readtext(
            image,
            detail=0,
            paragraph=True
        )

        if results:
            recognition_text = "AI: " + " ".join(results)
            assistant_message = "Text detected!"

        else:
            recognition_text = "AI: NO TEXT DETECTED"
            assistant_message = "Write clearly and try again."

    except Exception as error:
        recognition_text = "AI: RECOGNITION FAILED"
        assistant_message = "Check terminal for error."
        print("AI error:", error)

    finally:
        recognition_running = False


def start_recognition():
    global recognition_running

    if not AI_AVAILABLE:
        print("Install EasyOCR:")
        print("python -m pip install easyocr")
        return

    if not recognition_running:
        recognition_running = True

        threading.Thread(
            target=recognize_handwriting,
            daemon=True
        ).start()

def save_drawing():
    filename = f"drawing_{int(time.time())}.png"

    with canvas_lock:
        success = cv2.imwrite(
            filename,
            canvas.copy()
        )

    if success:
        print("Saved:", os.path.abspath(filename))
        return True

    print("Save failed.")
    return False


def draw_instruction_panel(output, mode):

    # Permanent top panel
    cv2.rectangle(
        output,
        (0, 0),
        (W, PANEL_H),
        (25, 25, 25),
        -1
    )

    
    cv2.putText(
        output,
        "AI VIRTUAL HANDWRITING PRO",
        (20, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 255),
        2,
        cv2.LINE_AA
    )

    
    cv2.putText(
        output,
        "MODE: " + mode,
        (20, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    
    cv2.putText(
        output,
        "COLOR: " + COLOR_NAMES[color_index],
        (250, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        COLORS[color_index],
        2,
        cv2.LINE_AA
    )

    
    cv2.putText(
        output,
        voice_status[:45],
        (600, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2,
        cv2.LINE_AA
    )

    
    cv2.putText(
        output,
        "1 FINGER: WRITE",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        "5 FINGERS: ERASE",
        (270, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 100, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        "1-4: COLORS",
        (560, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 255, 255),
        2,
        cv2.LINE_AA
    )

    
    cv2.putText(
        output,
        "E: CLEAR",
        (20, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        "S: SAVE",
        (200, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        "R: AI READ",
        (370, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        "V: VOICE",
        (570, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 255, 0),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        "Q: EXIT",
        (740, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    
    cv2.putText(
        output,
        recognition_text[:48],
        (850, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        assistant_message[:48],
        (850, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 255, 255),
        1,
        cv2.LINE_AA
    )

    return output


cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("Camera not found!")
    hands.close()
    raise SystemExit

print("AI Virtual Handwriting Pro started!")

# Create window only once
window_name = "AI Virtual Handwriting Pro"

cv2.namedWindow(
    window_name,
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    window_name,
    1280,
    720
)


try:
    while True:

        success, frame = cap.read()

        if not success:
            print("Cannot read camera.")
            break

        frame = cv2.flip(frame, 1)

        frame = cv2.resize(
            frame,
            (W, H)
        )

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        result = hands.process(rgb)

        mode = "READY"


        with state_lock:
            command = voice_command
            voice_command = ""

        if command:

            if "clear" in command or "erase all" in command:

                with canvas_lock:
                    canvas[:] = 0

                previous_x = 0
                previous_y = 0
                assistant_message = "Canvas cleared"

            elif "save" in command:

                if save_drawing():
                    assistant_message = "Drawing saved"

            elif "red" in command:
                color_index = 0

            elif "green" in command:
                color_index = 1

            elif "blue" in command:
                color_index = 2

            elif "yellow" in command:
                color_index = 3

            elif (
                "recognize" in command
                or "read text" in command
            ):
                start_recognition()

            elif "help" in command:
                assistant_message = (
                    "Draw, erase, save or change color"
                )


        if result.multi_hand_landmarks:

            hand = result.multi_hand_landmarks[0]
            lm = hand.landmark

            mp_draw.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            # Index fingertip
            x = int(lm[8].x * W)
            y = int(lm[8].y * H)

            x = max(0, min(W - 1, x))
            y = max(0, min(H - 1, y))

            index_up = lm[8].y < lm[6].y
            middle_up = lm[12].y < lm[10].y
            ring_up = lm[16].y < lm[14].y
            pinky_up = lm[20].y < lm[18].y

            
            thumb_up = lm[4].x < lm[3].x

            total_fingers = sum([
                index_up,
                middle_up,
                ring_up,
                pinky_up,
                thumb_up
            ])

            
            if total_fingers == 1 and index_up:

                mode = "WRITING"

                cv2.circle(
                    frame,
                    (x, y),
                    10,
                    COLORS[color_index],
                    -1
                )

                if previous_x != 0 or previous_y != 0:

                    with canvas_lock:
                        cv2.line(
                            canvas,
                            (previous_x, previous_y),
                            (x, y),
                            COLORS[color_index],
                            BRUSH_SIZE,
                            cv2.LINE_AA
                        )

                previous_x = x
                previous_y = y

            
            elif total_fingers == 5:

                mode = "ERASING"

                cv2.circle(
                    frame,
                    (x, y),
                    ERASER_SIZE,
                    (0, 0, 255),
                    3
                )

                with canvas_lock:
                    cv2.circle(
                        canvas,
                        (x, y),
                        ERASER_SIZE,
                        (0, 0, 0),
                        -1
                    )

                previous_x = 0
                previous_y = 0

            else:

                mode = "PAUSED"

                previous_x = 0
                previous_y = 0

        else:

            previous_x = 0
            previous_y = 0

      

        with canvas_lock:
            canvas_copy = canvas.copy()

        gray = cv2.cvtColor(
            canvas_copy,
            cv2.COLOR_BGR2GRAY
        )

        _, mask = cv2.threshold(
            gray,
            1,
            255,
            cv2.THRESH_BINARY
        )

        mask_inv = cv2.bitwise_not(mask)

        background = cv2.bitwise_and(
            frame,
            frame,
            mask=mask_inv
        )

        drawing = cv2.bitwise_and(
            canvas_copy,
            canvas_copy,
            mask=mask
        )

        output = cv2.add(
            background,
            drawing
        )


        output = draw_instruction_panel(
            output,
            mode
        )


        cv2.imshow(
            window_name,
            output
        )

 

        key = cv2.waitKey(1) & 0xFF

        if key in [
            ord("1"),
            ord("2"),
            ord("3"),
            ord("4")
        ]:

            color_index = int(chr(key)) - 1

        elif key in [ord("e"), ord("E")]:

            with canvas_lock:
                canvas[:] = 0

            previous_x = 0
            previous_y = 0

            recognition_text = "AI: CANVAS CLEARED"
            assistant_message = "Start drawing!"

        elif key in [ord("s"), ord("S")]:

            if save_drawing():
                assistant_message = "Drawing saved!"

        elif key in [ord("r"), ord("R")]:

            start_recognition()

        elif key in [ord("v"), ord("V")]:

            start_voice()

        elif key in [ord("q"), ord("Q")]:

            break

finally:

    cap.release()
    hands.close()
    cv2.destroyAllWindows()

    print("AI Virtual Handwriting Pro stopped.")