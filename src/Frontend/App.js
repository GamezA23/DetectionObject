import { useState } from "react";
import { StyleSheet,Text,View,TouchableOpacity,TouchableWithoutFeedback,Image } from "react-native";
import { API_URL } from '@env';
import { StatusBar } from "expo-status-bar";
import * as ImagePicker from "expo-image-picker";
import * as Speech from "expo-speech";

export default function App() {
  const [image, setImage] = useState(null);
  const [results, setResults] = useState([]);

  let lastTap = null;
  const DoubleTap = () => {
    const now = Date.now();
    const delay = 500;
    if (lastTap && now - lastTap < delay) {
      openCamera();
    } else {
      lastTap = now;
    }
  };
  
  const goBackToStart = () => {
    Speech.speak("ผู้ใช้งานได้ทำการกลับไปยังหน้าแรก");
    Speech.stop();
    setImage(null);
  };

  if (image) {
    Speech.stop();
    Speech.speak("คุณได้ถ่ายภาพแล้ว กรุณารอสักครู่");
  } else {
    Speech.stop();
    Speech.speak(
      "ยินดีต้อนรับสู่แอปตรวจจับวัตถุเพื่อช่วยเหลือผู้พิการทางสายตา"
    );
    Speech.speak("กรุณาแตะที่หน้าจอ 2ครั้ง เพื่อเข้าสู่กล้องเพื่อถ่ายรูป");
  }

  const openCamera = async () => {
    Speech.stop();
    Speech.speak("กำลังเปิดกล้อง");
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false,
      quality: 1,
    });

    if (!result.canceled) {
      setImage(result.assets[0].uri);
      await uploadImageToAPI(result.assets[0].uri);
    }
  };

  const uploadImageToAPI = async (imageUri) => {
    try {
      let filename = imageUri.split("/").pop();
      let match = /\.(\w+)$/.exec(filename);
      let type = match ? `image/${match[1]}` : `image`;
      let formData = new FormData();

      formData.append("file", {uri: imageUri,name: filename,type: type, });

      const response = await fetch(`${API_URL}/detect`, {method: "POST",body: formData,});
      const data = await response.json();

      if (data.message && data.message !== "") {
        Speech.speak(data.message, {
          onDone: () => {
            setTimeout(() => {
              Speech.speak("หากต้องการใช้งานอีกครั้งแตะตรงกลาง 1 ครั้ง เพื่อกลับไปยังหน้าแรก", {
              });
            }, 1000);
          },
        });
      } else {
        Speech.speak("ไม่สามารถระบุวัตถุในภาพได้", {
          onDone: () => {
            Speech.speak("หากต้องการใช้งานอีกครั้งแตะตรงกลาง 1 ครั้ง เพื่อกลับไปยังหน้าแรก", {
            });
          },
        });
      }
      console.log("ผลลัพธ์ที่ตรวจจับได้:", data.message);
    } catch (error) {
      Speech.speak("เกิดข้อผิดพลาดในการส่งภาพ");
      console.error(error);
    }
  };

  return (
    <TouchableWithoutFeedback onPress={!image ? DoubleTap : undefined}>
      <View style={styles.container}>
        {image ? (
          <>
            <TouchableOpacity onPress={goBackToStart}>
              <Image source={{ uri: image }} style={styles.image} />
            </TouchableOpacity>
          </>
        ) : (
          <Text style={styles.text}>กรุณาแตะที่หน้าจอ 2 ครั้ง</Text>
        )}
        <StatusBar style="auto" />
      </View>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontSize: 30,
    paddingHorizontal: 20,
    textAlign: "center",
  },
  image: {
    width: 300,
    height: 400,
    borderRadius: 10,
  },
});
