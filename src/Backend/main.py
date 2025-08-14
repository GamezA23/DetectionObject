from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image, ImageEnhance
import numpy as np
from collections import defaultdict
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("yolo11m.pt")
#เช็คclass ในโมเดล Yolo
#class_names = model.names
#num_classes = len(class_names)
#print("จำนวนคลาสทั้งหมด:", num_classes)
#print("ชื่อคลาส:", class_names)

#แปลชื่อคลาสเป็นภาษาไทย
class_name_th = {
    "spoon": "ช้อน",
    "fork": "ส้อม",
    "cup": "ถ้วย",    
    "orange": "ส้ม",           
    "dining table": "โต๊ะอาหาร", 
    "chair": "เก้าอี้",          
    "microwave": "ไมโครเวฟ",   
    "clock": "นาฬิกา",          
    "toothbrush": "แปรงสีฟัน",   
    "book": "หนังสือ",         
    "knife": "มีด",             
    "banana": "กล้วย",        
    "scissors": "กรรไกร",      
    "backpack": "เป้",         
    "bottle": "ขวด",          
    "couch": "โซฟา",        
    "tv": "ทีวี",            
    "bed": "เตียง",          
    "apple": "แอปเปิ้ล",       
    "remote": "รีโมต",          
}

#หน่วยวัดสำหรับแต่ละคลาส
class_unit_th = {
    "spoon": "คัน",
    "fork": "คัน",
    "cup": "ใบ",
    "orange": "ลูก",
    "dining table": "ตัว",
    "chair": "ตัว",
    "microwave": "เครื่อง",
    "clock": "เรือน",
    "toothbrush": "แท่ง",
    "book": "เล่ม",
    "knife": "เล่ม",
    "banana": "หวี",
    "scissors": "อัน",
    "backpack": "ใบ",
    "bottle": "ขวด",
    "couch": "ตัว",
    "tv": "เครื่อง",
    "bed": "เตียง",
    "apple": "ลูก",
    "remote": "อัน"
}

#ฟังก์ชันแปลงความสว่างเป็นลักซ์
def brightness_to_lux(avg_brightness):
    return (avg_brightness / 255) * 10000

#ฟังก์ชันแปลงลักซ์เป็นความสว่าง
def lux_to_brightness(lux):
    return (lux / 10000) * 255

#ฟังก์ชันตรวจสอบและปรับแสง
def check_and_adjust_light(image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        gray = image.convert("L")
        avg_brightness = np.mean(np.array(gray))
        lux = brightness_to_lux(avg_brightness)

        if 200 <= lux <= 1000:
            image.save(image_path)
            return lux
        else:
            target_lux = 300
            target_brightness = lux_to_brightness(target_lux)
            factor = target_brightness / avg_brightness

            enhancer = ImageEnhance.Brightness(image)
            adjusted = enhancer.enhance(factor)
            adjusted.save(image_path)
            return target_lux
    except Exception as e:
        print(f"Error in light adjustment: {e}")
        return 0, f"เกิดข้อผิดพลาด: {str(e)}"

#สรุปทิศทางการตรวจจับวัตถุ
def summarize_direction(L, C, R):
    if L and not C and not R: return "เจอวัตถุด้านซ้าย"
    if R and not L and not C: return "เจอวัตถุด้านขวา"
    if C and not L and not R: return "เจอวัตถุตรงกลาง"
    if L and R and not C:    return "เจอวัตถุด้านซ้ายและขวา"
    if L and C and not R:    return "เจอวัตถุด้านซ้ายกึ่งตรงกลาง"
    if R and C and not L:    return "เจอวัตถุด้านขวากึ่งตรงกลาง"
    if L and C and R:        return "เจอวัตถุด้านซ้าย ขวา และตรงกลาง"
    return ""

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    os.makedirs("temp", exist_ok=True)
    path = f"temp/{file.filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    # ปรับแสง (คงของเดิม)
    check_and_adjust_light(path)

    # ขนาดภาพ
    with Image.open(path) as im:
        width, height = im.size

    # รันโมเดล
    results = model(path)
    r = results[0]
    boxes = r.boxes
    names = r.names  # ชื่อคลาสจากโมเดล

    print("วัตถุทั้งหมดที่ตรวจจับได้")
    # เก็บ count ต่อคลาส/ทิศ
    # counts[class] = {"L": x, "C": y, "R": z}
    counts = defaultdict(lambda: {"L": 0, "C": 0, "R": 0})

    # กรองด้วย confidence
    conf_th = 0.8

    # ค่าขอบเขตซ้าย-กลาง-ขวา
    left_edge = width / 3.0
    right_edge = width * 2.0 / 3.0

    # เดินกล่อง
    for b in boxes:
        conf = float(b.conf[0])
        if conf < conf_th:
            continue

        cls_id = int(b.cls[0])
        # names อาจเป็น list หรือ dict -> ดึงให้ชัวร์
        cls_name = names[cls_id] if not isinstance(names, dict) else names.get(cls_id, str(cls_id))

        print(f" - class: {cls_name}, confidence: {conf:.2f}")

        # สนใจเฉพาะคลาสที่มี mapping ภาษาไทย
        if cls_name not in class_name_th:
            continue

        x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
        center_x = (x1 + x2) / 2.0

        if center_x < left_edge:
            sector = "L"
        elif center_x > right_edge:
            sector = "R"
        else:
            sector = "C"

        counts[cls_name][sector] += 1

    # ลบไฟล์ชั่วคราวให้เรียบร้อย
    try:
        os.remove(path)
    except Exception:
        pass

    if not counts:
        return {"message": "ไม่สามารถระบุวัตถุในภาพได้"}

    # ฟอร์แมตข้อความ: ต่อทิศเฉพาะที่นับได้ > 0
    def format_one_class(cls_en, per_dir):
        th_label = class_name_th.get(cls_en, cls_en)
        unit = class_unit_th.get(cls_en, "")
        bits = []
        if per_dir["L"] > 0:
            bits.append(f"ทางซ้าย {per_dir['L']} {unit}".strip())
        if per_dir["C"] > 0:
            bits.append(f"ตรงกลาง {per_dir['C']} {unit}".strip())
        if per_dir["R"] > 0:
            bits.append(f"ทางขวา {per_dir['R']} {unit}".strip())

        # ไม่มีทิศไหนเกินศูนย์ (กันกรณีแปลก)
        if not bits:
            return ""

        # ถ้ามีแค่คลาสเดียวในภาพ ไม่ต้องใส่ชื่อคลาสนำหน้า
        return " และ ".join(bits)

    # ถ้ามีหลายคลาส จะแยกเป็นคลาสๆ พร้อมชื่อคลาสนำหน้า
    if len(counts) == 1:
        only_cls = next(iter(counts.keys()))
        msg = format_one_class(only_cls, counts[only_cls])
        return {"message": msg if msg else "ไม่สามารถระบุวัตถุในภาพได้"}
    else:
        parts = []
        for cls_en, per_dir in counts.items():
            msg_each = format_one_class(cls_en, per_dir)
            if msg_each:
                parts.append(f"{class_name_th.get(cls_en, cls_en)}: {msg_each}")
        final_msg = ", ".join(parts) if parts else "ไม่สามารถระบุวัตถุในภาพได้"
        return {"message": final_msg}