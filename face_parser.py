import math
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from skimage import transform as trans
from typing import Tuple, Union
from scipy.spatial.transform import Rotation as R


class FaceParser():
    def __init__(self, max_num_faces=1, min_detection_confidence=0.5,
                 min_tracking_confidence=0.5, static_image_mode=True):
        self.__mp_face_mesh = mp.solutions.face_mesh
        self.__face_mesh = self.__mp_face_mesh.FaceMesh(
            max_num_faces=max_num_faces,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            static_image_mode=static_image_mode)
        self.__presence_thr = 0.5
        self.__visibility_thr = 0.5

        self.__mp_pose = mp.solutions.pose
        self.__body_pose = self.__mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence)

    @staticmethod
    def __normalized_to_pixel_coordinates(
        normalized_x: float, normalized_y: float, image_width: int,
        image_height: int) -> Union[None, Tuple[int, int]]:
        """Converts normalized value pair to pixel coordinates."""

        # Checks if the float value is between 0 and 1.
        def is_valid_normalized_value(value: float) -> bool:
            return (value > 0 or math.isclose(0, value)) and \
                (value < 1 or math.isclose(1, value))

        if not (is_valid_normalized_value(normalized_x) and
                is_valid_normalized_value(normalized_y)):
            # TODO: Draw coordinates even if it's outside of the image bounds.
            return None
        x_px = min(math.floor(normalized_x * image_width), image_width - 1)
        y_px = min(math.floor(normalized_y * image_height), image_height - 1)
        return x_px, y_px

    def __get_face_key_landmarks(self,
        face_landmarks: landmark_pb2.NormalizedLandmarkList,
        image_cols: int, image_rows: int):
        key_landmarks = {}
        norm_key_landmarks = {}
        for idx, landmark in enumerate(face_landmarks.landmark):
            if idx not in (4, 33, 61, 129, 133, 168, 263, 308, 358, 362):
                continue
            if ((landmark.HasField('visibility') and
                landmark.visibility < self.__visibility_thr) or
                (landmark.HasField('presence') and
                landmark.presence < self.__presence_thr)):
                continue
            landmark_px = self.__normalized_to_pixel_coordinates(
                normalized_x=landmark.x,
                normalized_y=landmark.y,
                image_width=image_cols,
                image_height=image_rows)
            if landmark_px:
                key_landmarks[idx] = (landmark_px, landmark.z)
                norm_key_landmarks[idx] = (landmark.x, landmark.y, landmark.z)

        face_key_landmarks = {}
        norm_face_key_landmarks = {}
        # Face landmarks:
        # 0: Left eye outer corner (33)
        # 1: Left eye inner corner (133)
        # 2: Right eye inner corner (362)
        # 3: Right eye outer corner (263)
        # 4: Nose tip (4)
        # 5: Mouth left corner (61)
        # 6: Mouth right corner (308)
        if 33 in key_landmarks:
            face_key_landmarks[0] = key_landmarks[33]
            norm_face_key_landmarks[0] = norm_key_landmarks[33]
        if 133 in key_landmarks:
            face_key_landmarks[1] = key_landmarks[133]
            norm_face_key_landmarks[1] = norm_key_landmarks[133]
        if 362 in key_landmarks:
            face_key_landmarks[2] = key_landmarks[362]
            norm_face_key_landmarks[2] = norm_key_landmarks[362]
        if 263 in key_landmarks:
            face_key_landmarks[3] = key_landmarks[263]
            norm_face_key_landmarks[3] = norm_key_landmarks[263]
        if 4 in key_landmarks:
            face_key_landmarks[4] = key_landmarks[4]
            norm_face_key_landmarks[4] = norm_key_landmarks[4]
        if 61 in key_landmarks:
            face_key_landmarks[5] = key_landmarks[61]
            norm_face_key_landmarks[5] = norm_key_landmarks[61]
        if 308 in key_landmarks:
            face_key_landmarks[6] = key_landmarks[308]
            norm_face_key_landmarks[6] = norm_key_landmarks[308]

        return face_key_landmarks, norm_face_key_landmarks

    def __get_body_face_key_landmarks(self, image):
        face_key_landmarks = {}
        norm_face_key_landmarks = {}
        results = self.__body_pose.process(image)

        if not results.pose_landmarks:
            return face_key_landmarks, norm_face_key_landmarks

        # Face landmarks:
        # 0: Left eye outer corner
        # 1: Left eye inner corner
        # 2: Right eye inner corner
        # 3: Right eye outer corner
        # 4: Nose tip
        # 5: Mouth left corner
        # 6: Mouth right corner
        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.RIGHT_EYE_OUTER]
        norm_face_key_landmarks[0] = (coords.x, coords.y, coords.z)
        face_key_landmarks[0] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.RIGHT_EYE_INNER]
        norm_face_key_landmarks[1] = (coords.x, coords.y, coords.z)
        face_key_landmarks[1] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.LEFT_EYE_INNER]
        norm_face_key_landmarks[2] = (coords.x, coords.y, coords.z)
        face_key_landmarks[2] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.LEFT_EYE_OUTER]
        norm_face_key_landmarks[3] = (coords.x, coords.y, coords.z)
        face_key_landmarks[3] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.NOSE]
        norm_face_key_landmarks[4] = (coords.x, coords.y, coords.z)
        face_key_landmarks[4] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.MOUTH_RIGHT]
        norm_face_key_landmarks[5] = (coords.x, coords.y, coords.z)
        face_key_landmarks[5] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        coords = results.pose_landmarks.landmark[\
            self.__mp_pose.PoseLandmark.MOUTH_LEFT]
        norm_face_key_landmarks[6] = (coords.x, coords.y, coords.z)
        face_key_landmarks[6] = \
            ((coords.x * image.shape[1], coords.y * image.shape[0]),
            coords.visibility)

        return face_key_landmarks, norm_face_key_landmarks

    @staticmethod
    def __truncate_to_valid_rect(rect, img_w, img_h):
        tl_x = int(max(0, min(img_w - 1, rect[0])))
        tl_y = int(max(0, min(img_h - 1, rect[1])))
        br_x = int(max(0, min(img_w, rect[0] + rect[2])))
        br_y = int(max(0, min(img_h, rect[1] + rect[3])))
        width = int(max(0, br_x - tl_x))
        height = int(max(0, br_y - tl_y))
        return [tl_x, tl_y, width, height]

    @staticmethod
    def __get_face_bounding_box(key_landmarks, image_cols, image_rows):
        min_x = image_cols
        min_y = image_rows
        max_x = 0
        max_y = 0
        for key_landmark in key_landmarks.values():
            if key_landmark[0][0] <= min_x:
                min_x = key_landmark[0][0]
            if key_landmark[0][1] <= min_y:
                min_y = key_landmark[0][1]
            if key_landmark[0][0] >= max_x:
                max_x = key_landmark[0][0]
            if key_landmark[0][1] >= max_y:
                max_y = key_landmark[0][1]
        mean_x = (min_x + max_x) / 2
        mean_y = (min_y + max_y) / 2
        width = 2.65 * ((max_x - min_x) + (max_y - min_y)) / 2
        height = width

        return [int(mean_x - 0.52 * width), int(mean_y - 0.54 * height), \
            int(width), int(height)]

    def __get_head_angles(self, norm_key_landmarks):
        # Camera reference: +X left, +Y up, and +Z backwards (right handed)
        lids = [0, 1, 2]
        rids = [3, 2, 1]

        lid = None
        for id in lids:
            if id in norm_key_landmarks:
                lid = id
                break
        for id in rids:
            if id in norm_key_landmarks:
                rid = id
                break

        # If landmark ids are not in list, return default values
        lands_missed = len(norm_key_landmarks) < 7
        if lid is None or lands_missed:
            rot = R.identity()
            return rot.as_euler('xyz', degrees=True)

        if lid != rid and lid in norm_key_landmarks and \
            rid in norm_key_landmarks:
            x = np.array(np.array(norm_key_landmarks[rid]) - \
                np.array(norm_key_landmarks[lid]))
            x /= np.linalg.norm(x)
        else:
            x = np.array([1.0, 0, 0])
        if 1 in norm_key_landmarks and 2 in norm_key_landmarks and \
            5 in norm_key_landmarks and 6 in norm_key_landmarks:
            y = np.array(0.5 * (np.array(norm_key_landmarks[5]) + \
                np.array(norm_key_landmarks[6])) - \
                    0.5 * (np.array(norm_key_landmarks[1]) + \
                        np.array(norm_key_landmarks[2])))
            y /= np.linalg.norm(y)
        else:
            y = np.array([0, -1.0, 0])
        z = np.cross(x, y)
        z /= np.linalg.norm(z)

        rot = R.from_matrix([[x[0], y[0], z[0]],
                             [x[1], y[1], z[1]],
                             [x[2], y[2], z[2]]])

        return rot.as_euler('xyz', degrees=True)

    def detect_faces_lms_ang(self, image):
        """
        Detects faces, facial landmarks and head angles on the image.
        """
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.__face_mesh.process(image)
        image_rows, image_cols, _ = image.shape
        faces = []
        landmarks = []
        angles = []
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                key_landmarks, norm_key_landmarks = \
                    self.__get_face_key_landmarks(
                        face_landmarks, image_cols, image_rows)
                # key_landmarks, norm_key_landmarks = \
                #     self.__get_body_face_key_landmarks(image)

                bounding_box = self.__get_face_bounding_box(
                    key_landmarks, image_cols, image_rows)
                bounding_box = self.__truncate_to_valid_rect(
                    bounding_box, image_cols, image_rows)

                head_angles = self.__get_head_angles(norm_key_landmarks)

                landmarks.append(key_landmarks)
                faces.append(bounding_box)
                angles.append(head_angles.tolist())

        return faces, landmarks, angles
