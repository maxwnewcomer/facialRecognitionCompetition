from imutils.video import VideoStream
from imutils.video import FPS
from tensorflow import keras
from datetime import datetime
import numpy as np
import argparse
import imutils
import pickle
import time
import cv2
import os

def recognize_video(detectorPath, embedding_model, recognizerPath, label, confidenceLim, projectPath):
	print("[INFO] loading face detector...")
	protoPath = os.path.sep.join([detectorPath, "deploy.prototxt"])
	modelPath = os.path.sep.join([detectorPath, "res10_300x300_ssd_iter_140000.caffemodel"])
	detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)

	print("[INFO] loading face recognizer...")
	embedder = cv2.dnn.readNetFromTorch(embedding_model)
	recognizer = keras.models.load_model(recognizerPath)
	le = pickle.loads(open(label, "rb").read())

	print("[INFO] starting video stream...")
	vs = VideoStream(src=0).start()
	time.sleep(1)
	fps = FPS().start()

	total_saved = 0
	mostrecentupload = datetime.now()

	while True:
		frame = vs.read()
		frame = imutils.resize(frame, width=600)
		(h, w) = frame.shape[:2]
		imageBlob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0), swapRB=False, crop=False)
		detector.setInput(imageBlob)
		detections = detector.forward()
		for i in range(0, detections.shape[2]):
			confidence = detections[0, 0, i, 2]
			if confidence > confidenceLim:
				box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
				(startX, startY, endX, endY) = box.astype("int")
				face = frame[startY:endY, startX:endX]
				(fH, fW) = face.shape[:2]
				if fW < 20 or fH < 20:
					continue
				faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False)
				embedder.setInput(faceBlob)
				vec = embedder.forward()
				preds = recognizer.predict(vec)[0]
				j = np.argmax(preds)
				proba = preds[j]
				name = le.classes_[j]
				text = "{}: {:.2f}%".format(name, proba * 100)
				y = startY - 10 if startY - 10 > 10 else startY + 10
				# if (proba > confidenceLim + .25) or (proba <= 1 and proba >= .90):
				# 	try:
				# 		if((datetime.now() - mostrecentupload).total_seconds() > 15):
				# 			cv2.imwrite('{}/dataset/{}/{}.jpg'.format(projectPath, name, datetime.now().strftime("%d%m%Y::%H:%M:%S")), frame)
				# 			print("[INFO] Saving image to data from video stream...")
				# 			mostrecentupload = datetime.now()
				# 			total_saved += 1
				# 	except:
				# 		print("[ERROR] coudn't save image...")
				cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 0, 255), 2)
				cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
		fps.update()
		cv2.imshow("Frame", frame)
		key = cv2.waitKey(1) & 0xFF
		if key == ord("q"):
			break

	fps.stop()
	print("[INFO] elasped time: {:.2f}secs".format(fps.elapsed()))
	print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))
	print("[INFO] total saved pictures: {}".format(total_saved))
	print("[DONE] stream terminated")

	# do a bit of cleanup
	cv2.destroyAllWindows()
	vs.stop()
