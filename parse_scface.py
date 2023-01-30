import cv2
import glob, os
import csv
from scipy.spatial.transform import Rotation as R
from face_parser import FaceParser


def main(src_data_dir, dst_data_dir, show_imgs, norm_width):
    data_src_string = "{}/*.jpg".format(src_data_dir)
    output_file = os.path.join(dst_data_dir, 'attributes.csv')
    f = open(output_file, 'w', encoding='UTF8', newline='')
    writer = csv.writer(f)
    header = ['image_path', 'face_x', 'face_y', 'face_w', 'face_h',
        'l_eye_outer_corner_x', 'l_eye_outer_corner_y',
        'l_eye_inner_corner_x', 'l_eye_inner_corner_y',
        'r_eye_outer_corner_x', 'r_eye_outer_corner_y',
        'r_eye_inner_corner_x', 'r_eye_inner_corner_y',
        'nose_tip_x', 'nose_tip_y',
        'mouth_l_corner_x', 'mouth_l_corner_y',
        'mouth_r_corner_x', 'mouth_r_corner_y',
        'pitch', 'yaw', 'roll']
    writer.writerow(header)

    for file_full_path in glob.glob(data_src_string):
        filepath = os.path.join(src_data_dir, file_full_path)
        print("Parsing " + file_full_path + "...")
        image = cv2.imread(filepath)
        if image.any():
            faces, landmarks, angles = face_parser.detect_faces_lms_ang(image)
            if len(faces) == 0:
                print("WARNING: No face found. Image " + file_full_path + \
                    " skipped.")
                continue

            annotation = [file_full_path]

            # We assume one face only
            annotation.append(faces[0][0])
            annotation.append(faces[0][1])
            annotation.append(faces[0][2])
            annotation.append(faces[0][3])

            for landmark in landmarks[0].values():
                annotation.append(landmark[0][0])
                annotation.append(landmark[0][1])

            annotation.append(angles[0][0])
            annotation.append(angles[0][1])
            annotation.append(angles[0][2])
            writer.writerow(annotation)

            if show_imgs:
                scale = norm_width / image.shape[1]
                resized = cv2.resize(image, (norm_width, \
                    int(image.shape[0] * scale)))

                rx1 = int(faces[0][0] * scale)
                ry1 = int(faces[0][1] * scale)
                rx2 = int(rx1 + faces[0][2] * scale)
                ry2 = int(ry1 + faces[0][3] * scale)

                cv2.rectangle(resized, (rx1, ry1), (rx2, ry2), (0, 0, 255), 1)
                for landmark in landmarks[0].values():
                    cv2.circle(resized, (int(landmark[0][0] * scale),
                        int(landmark[0][1] * scale)), 1, (0, 255, 0), 1)

                head_pos = (int((rx1 + rx2) / 2), int((ry1 + ry2) / 2))
                rot = R.from_euler('xyz', angles[0], degrees=True).as_matrix()
                x_pos = (head_pos[0] + int(50 * rot[0][0]), head_pos[1] + \
                    int(50 * rot[1][0]))
                y_pos = (head_pos[0] + int(50 * rot[0][1]), head_pos[1] + \
                    int(50 * rot[1][1]))
                z_pos = (head_pos[0] + int(50 * rot[0][2]), head_pos[1] + \
                    int(50 * rot[1][2]))
                cv2.line(resized, head_pos, x_pos, color=(0, 0, 255),
                    thickness=1)
                cv2.line(resized, head_pos, y_pos, color=(0, 255, 0),
                    thickness=1)
                cv2.line(resized, head_pos, z_pos, color=(255, 0, 0),
                    thickness=1)
                cv2.imshow("Output", resized)
                wkey = cv2.waitKey(0)

            print("Image " + file_full_path + " processed.")

    f.close()
    print("Data generation finished. Data saved in: " + output_file)

if __name__ == "__main__":
    src_data_dir = "/home/jmacarulla/video_resources/image_datasets/SCface/mugshot_rotation_all"
    # src_data_dir = "/home/andrea/PycharmProjects/SQL-DB-Face-Image/image_datasets/forenface"
    # dst_data_dir = "/home/andrea/PycharmProjects/SQL-DB-Face-Image/"
    # src_data_dir = '/home/jmacarulla/video_resources/image_datasets/lfw/George_W_Bush'
    dst_data_dir = "."
    show_imgs = False
    norm_width = 640

    main(src_data_dir, dst_data_dir, show_imgs, norm_width)
