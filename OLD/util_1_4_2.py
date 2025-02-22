import cv2
import mediapipe as mp
import pyautogui
import math
import win32api
import win32con
import time
import numpy as np
from PIL import Image


from os import system

import tensorflow as tf

from matplotlib import pyplot as plt
from matplotlib import animation

tf.config.experimental.set_visible_devices([], 'GPU')
from PyQt5 import QtCore, QtGui, QtWidgets

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from loading import *


import datetime
import sys
import os


'''
키 코드 링크 : https://lab.cliel.com/entry/%EA%B0%80%EC%83%81-Key-Code%ED%91%9C
'''


# physical_devices = tf.config.list_physical_devices('GPU')
# print(physical_devices)
# tf.config.experimental.set_memory_growth(physical_devices[0], True)

# For webcam input:
# hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# x_size, y_size = pyautogui.size().width, pyautogui.size().height
x_size, y_size = 1366, 768

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
# mp_face_detection = mp.solutions.face_detection
# mp_pose = mp.solutions.pose

# now_click = False
# now_click2 = False
straight_line = False
rectangular = False
circle = False

gesture_int = 0


USE_TENSORFLOW = True
# USE_DYNAMIC = True

LEFT = True

import json

with open('../setting.json', encoding='UTF8') as json_file:
    json_data = json.load(json_file)

language_setting = json_data["LANGUAGE"]
DARK_MODE = True if json_data["DARK_MODE"] == "True" else False
LEFT = True if json_data["LEFT"] == "True" else False

MOUSE_USE = False
CLICK_USE = False
WHEEL_USE = False
DRAG_USE = False
BOARD_COLOR = 'w'

VISUALIZE_GRAPH = False
EXIT_SURVEY = False

gesture_check = False
mode_global = 0
pen_color = ''
laser_state = False
laser_num = 0

'''
mark_pixel : 각각의 랜드마크
finger_open : 손 하나가 갖고있는 랜드마크들
Gesture : 손의 제스처를 판단하기 위한 랜드마크들의 Queue
'''


# TODO 손가락 굽힘 판단, 손바닥 상태, 오른손 왼손 확인
class Handmark:
    def __init__(self):
        # self._p_list = mark_p
        self.finger_state = [0 for _ in range(5)]
        self.palm_vector = np.array([0., 0., 0.])
        self.finger_vector = np.array([0., 0., 0.])
        # self.thumb, self.index, self.middle, self.ring, self.pinky = np.array()
        # self.finger_angle_list = np.array()

    @property
    def p_list(self):
        return self._p_list

    @p_list.setter
    def p_list(self, new_p):
        self._p_list = new_p

    def return_flatten_p_list(self):
        """
        :return: flatten p_list information
        """
        output = []
        for local_mark_p in self._p_list:
            # print('type', type(local_mark_p))
            output.extend(local_mark_p.to_list())
        return output

    # 엄지 제외
    @staticmethod
    def get_finger_angle(finger):
        l1 = finger[0] - finger[1]
        l2 = finger[3] - finger[1]
        l1_ = np.array([l1[0], l1[1], l1[2]])
        l2_ = np.array([l2[0], l2[1], l2[2]])
        return np.arccos(np.dot(l1_, l2_) / (norm(l1) * norm(l2)))

    @staticmethod
    def get_angle(l1, l2):
        """
        :param l1: numpy_vector 1
        :param l2: numpy_vector 2
        :return: angle between l1 and l2
        """
        l1_ = np.array([l1[0], l1[1], l1[2]])
        l2_ = np.array([l2[0], l2[1], l2[2]])
        return np.arccos(np.dot(l1_, l2_) / (norm(l1) * norm(l2)))

    def get_finger_angle_thumb(self, finger):
        l1 = finger[0] - finger[1]
        l2 = finger[1] - finger[2]
        return self.get_angle(l1, l2)

    def get_palm_vector(self):
        l1 = self._p_list[17] - self._p_list[0]
        l2 = self._p_list[5] - self._p_list[0]
        l1_ = np.array([l1[0], l1[1], l1[2]])
        l2_ = np.array([l2[0], l2[1], l2[2]])

        self.palm_vector = np.cross(l1_, l2_)
        self.palm_vector = self.palm_vector / vector_magnitude(self.palm_vector)
        # print(vector_magnitude((self.palm_vector)))
        return self.palm_vector

    def get_finger_vector(self):
        l0 = self._p_list[5] - self._p_list[0]
        self.finger_vector = np.array(l0)
        self.finger_vector = self.finger_vector / vector_magnitude(self.finger_vector)
        # print(vector_magnitude((self.finger_vector)))
        return self.finger_vector

    # True 펴짐 False 내림
    def return_finger_state(self, experiment_mode=False):
        self.thumb = [self._p_list[i] for i in range(1, 5)]
        self.index = [self._p_list[i] for i in range(5, 9)]
        self.middle = [self._p_list[i] for i in range(9, 13)]
        self.ring = [self._p_list[i] for i in range(13, 17)]
        self.pinky = [self._p_list[i] for i in range(17, 21)]

        # TODO 각 손가락 각도 근거로 손가락 굽힘 판단
        self.finger_angle_list = np.array([self.get_finger_angle(self.thumb),
                                           self.get_finger_angle(self.index),
                                           self.get_finger_angle(self.middle),
                                           self.get_finger_angle(self.ring),
                                           self.get_finger_angle(self.pinky)])
        finger_angle_threshold = np.array([2.8, 1.5, 2.2, 2.2, 2.4])
        self.finger_state_angle = np.array(self.finger_angle_list > finger_angle_threshold, dtype=int)

        # TODO 각 손가락 거리정보 근거로 손가락 굽힘 판단
        self.finger_distance_list = np.array(
            [get_distance(self.thumb[3], self.pinky[0]) / get_distance(self.index[0], self.pinky[0]),
             get_distance(self.index[3], self.index[0]) / get_distance(self.index[0], self.index[1]),
             get_distance(self.middle[3], self.middle[0]) / get_distance(self.middle[0], self.middle[1]),
             get_distance(self.ring[3], self.ring[0]) / get_distance(self.ring[0], self.ring[1]),
             get_distance(self.pinky[3], self.pinky[0]) / get_distance(self.pinky[0], self.pinky[1])])
        # print(self.finger_distance_list)
        finger_distance_threshold = np.array([1.5, 1.8, 2, 2, 2])
        self.finger_state_distance = np.array(self.finger_distance_list > finger_distance_threshold, dtype=int)

        # TODO 손가락과 손바닥 이용해 손가락 굽힘 판단
        self.hand_angle_list = np.array([self.get_angle(self.thumb[1] - self._p_list[0], self.thumb[3] - self.thumb[1]),
                                         self.get_angle(self.index[0] - self._p_list[0], self.index[3] - self.index[0]),
                                         self.get_angle(self.middle[0] - self._p_list[0],
                                                        self.middle[3] - self.middle[0]),
                                         self.get_angle(self.ring[0] - self._p_list[0], self.ring[3] - self.ring[0]),
                                         self.get_angle(self.pinky[0] - self._p_list[0],
                                                        self.pinky[3] - self.pinky[0])])
        # print(self.hand_angle_list)
        hand_angle_threshold = np.array([0.7, 1.7, 1.5, 1.5, 1.3])
        self.hand_state_angle = np.array(self.hand_angle_list < hand_angle_threshold, dtype=int)
        # print(self.finger_angle_list, self.finger_distance_list, self.hand_angle_list)
        self.input = np.concatenate((self.finger_angle_list, self.finger_distance_list, self.hand_angle_list))

        # print(predict_static(self.input))
        # print(np.round(self.finger_angle_list, 3), np.round(self.finger_distance_list, 3), np.round(self.hand_angle_list, 3))
        # print(self.finger_state_angle, self.finger_state_distance, self.hand_state_angle)

        self.result = self.finger_state_angle + self.finger_state_distance + self.hand_state_angle > 1
        # print(self.result)
        if experiment_mode == False:
            return self.result
        else:
            return np.round(self.finger_angle_list, 3), np.round(self.finger_distance_list, 3), np.round(
                self.hand_angle_list, 3)

    def return_finger_info(self):
        self.thumb = [self._p_list[i] for i in range(1, 5)]
        self.index = [self._p_list[i] for i in range(5, 9)]
        self.middle = [self._p_list[i] for i in range(9, 13)]
        self.ring = [self._p_list[i] for i in range(13, 17)]
        self.pinky = [self._p_list[i] for i in range(17, 21)]

        # TODO 각 손가락 각도 근거로 손가락 굽힘 판단
        self.finger_angle_list = np.array([self.get_finger_angle(self.thumb),
                                           self.get_finger_angle(self.index),
                                           self.get_finger_angle(self.middle),
                                           self.get_finger_angle(self.ring),
                                           self.get_finger_angle(self.pinky)])

        # TODO 각 손가락 거리정보 근거로 손가락 굽힘 판단
        self.finger_distance_list = np.array(
            [get_distance(self.thumb[3], self.pinky[0]) / get_distance(self.index[0], self.pinky[0]),
             get_distance(self.index[3], self.index[0]) / get_distance(self.index[0], self.index[1]),
             get_distance(self.middle[3], self.middle[0]) / get_distance(self.middle[0], self.middle[1]),
             get_distance(self.ring[3], self.ring[0]) / get_distance(self.ring[0], self.ring[1]),
             get_distance(self.pinky[3], self.pinky[0]) / get_distance(self.pinky[0], self.pinky[1])])
        # print(self.finger_distance_list)

        # TODO 손가락과 손바닥 이용해 손가락 굽힘 판단
        self.hand_angle_list = np.array([self.get_angle(self.thumb[1] - self._p_list[0], self.thumb[3] - self.thumb[1]),
                                         self.get_angle(self.index[0] - self._p_list[0], self.index[3] - self.index[0]),
                                         self.get_angle(self.middle[0] - self._p_list[0],
                                                        self.middle[3] - self.middle[0]),
                                         self.get_angle(self.ring[0] - self._p_list[0], self.ring[3] - self.ring[0]),
                                         self.get_angle(self.pinky[0] - self._p_list[0],
                                                        self.pinky[3] - self.pinky[0])])
        # print(self.hand_angle_list)
        # print(self.finger_angle_list, self.finger_distance_list, self.hand_angle_list)
        self.input = np.concatenate((self.finger_angle_list, self.finger_distance_list, self.hand_angle_list))
        return self.input

    def return_18_info(self):
        output = self.return_finger_info()
        output = np.concatenate((output, self.palm_vector))
        return output

    def return_21_info(self):
        output = self.return_finger_info()
        output = np.concatenate((output, self.palm_vector, self.finger_vector))
        return output


# TODO Gesture 판단, 일단은 15프레임 (0.5초)의 Queue로?
# class Gesture:
#     GESTURE_ARRAY_SIZE = 7
#     GESTURE_STATIC_SIZE = 15
#
#     def __init__(self):
#         self.palm_data = [np.array([0, 0, 0]) for _ in range(Gesture.GESTURE_ARRAY_SIZE)]
#         self.d_palm_data = [np.array([0, 0, 0]) for _ in range(Gesture.GESTURE_ARRAY_SIZE)]  # palm_data의 차이를 기록할 list
#
#         self.location_data = [[0.1, 0.1, 0.1] for _ in range(Gesture.GESTURE_ARRAY_SIZE)]
#         self.finger_data = [np.array([0, 0, 0, 0, 0]) for _ in range(Gesture.GESTURE_ARRAY_SIZE)]
#         self.gesture_data = [0] * Gesture.GESTURE_STATIC_SIZE
#         self.gesture_signal = [False] * Gesture.GESTURE_STATIC_SIZE
#
#     @staticmethod
#     def get_location(p):  # p는 프레임 수 * 좌표 세개
#         x_mean, y_mean, z_mean = 0, 0, 0
#         for i in range(len(p) - 1):
#             x_mean += p[i].x
#             y_mean += p[i].y
#             z_mean += p[i].z
#         x_mean, y_mean, z_mean = x_mean / (len(p) - 1), y_mean / (len(p) - 1), z_mean / (len(p) - 1)
#         return [x_mean, y_mean, z_mean]
#
#     @staticmethod
#     def remove_outlier(target):  # 1D numpy array 최대/최소 제거:
#         for i in range(target.shape[0]):
#             if target[i] == np.max(target):
#                 max_i = i
#             if target[i] == np.min(target):
#                 min_i = i
#         output = np.delete(target, (min_i, max_i))
#         return output
#
#     def update(self, handmark, gesture_num, signal):
#         # print(self.get_location(handmark._p_list))
#         self.palm_data.insert(0, handmark.palm_vector)
#         self.d_palm_data.insert(0, (self.palm_data[1] - handmark.palm_vector) * 1000)
#         self.location_data.insert(0, Gesture.get_location(handmark._p_list))  # location data는 (프레임 수) * 22 * Mark_p 객체
#         self.finger_data.insert(0, handmark.finger_vector)
#         self.gesture_data.insert(0, gesture_num)
#         self.gesture_signal.insert(0, signal)
#         # print(gesture_num)
#         # print(handmark.palm_vector)
#
#         self.palm_data.pop()
#         self.d_palm_data.pop()
#         self.location_data.pop()
#         self.finger_data.pop()
#         self.fv = handmark.finger_vector
#         self.gesture_data.pop()
#         self.gesture_signal.pop()
#
#         # print(self.palm_data[0], self.finger_data[0], self.location_data[0])
#         # print(handmark.palm_vector * 1000)
#
#     # handmark 지닌 10개의 프레임이 들어온다...
#     def detect_gesture(self):  # 이 최근꺼
#         global gesture_check
#         # print(self.gesture_signal)
#         # print(gesture_check)
#         if (gesture_check == True) or (self.gesture_signal.count(True) < 8):
#             # print(self.gesture_data)
#             return -1
#         # print(self.gesture_signal)
#
#         # print('swipe')
#         # i가 작을수록 더 최신 것
#         ld_window = self.location_data[2:]
#         x_classifier = np.array(ld_window[:-1])[:, 0] - np.array(ld_window[1:])[:, 0]
#         y_classifier = np.array(ld_window[:-1])[:, 1] - np.array(ld_window[1:])[:, 1]
#         x_classifier = self.remove_outlier(x_classifier)
#         y_classifier = self.remove_outlier(y_classifier)
#
#         # print(np.mean(x_classifier), np.mean(y_classifier))
#         # if np.mean(x_classifier) >
#
#         # x_classfication = self.d_location_data[:][0]
#         # y_classfication = self.d_location_data[:][1]
#         # print(x_classfication, y_classfication)
#
#         # 왼쪽 X감소 오른쪽 X증가
#         # 위 y감소 아래 y증가
#
#         x_mean, y_mean = np.mean(x_classifier), np.mean(y_classifier)
#         # print(x_mean, y_mean)
#
#         # 동적 제스처 - LEFT
#         # print(x_mean)
#         if y_mean != 0:
#             if x_mean / abs(y_mean) < -1.5 and x_mean < -0.03:
#                 # print('LEFT')
#                 condition1 = condition2 = condition3 = 0
#                 angle_threshold = [0., 0., -1.]
#                 angle_min = 3
#
#                 for i in range(Gesture.GESTURE_ARRAY_SIZE - 1):
#                     # print(get_angle(self.palm_data[i], angle_threshold) < 1.5)
#                     if get_angle(self.palm_data[i], angle_threshold) < 1.5:
#                         condition1 += 1
#
#                 condition_sum = condition1
#
#                 if condition_sum > 4:
#                     print("LEFT")
#                     # win32api.keybd_event(0x27, 0, 0, 0)
#                     return -1
#
#             # 동적 제스처 - RIGHT
#             if x_mean / abs(y_mean) > 1.5 and x_mean > 0.03:
#                 # print('RIGHT')
#                 condition1 = condition2 = condition3 = 0
#
#                 angle_threshold = [0., 0., -1.]
#                 for i in range(Gesture.GESTURE_ARRAY_SIZE - 1):
#                     if get_angle(self.palm_data[i], angle_threshold) < 1.5:
#                         condition1 += 1
#
#                 condition_sum = condition1
#
#                 if condition_sum > 4:
#                     print("RIGHT")
#                     # win32api.keybd_event(0x27, 0, 0, 0)
#                     return -1
#
#     def gesture_LRUD(self):  # 상하좌우 변화량 판단
#         LR_trigger, UD_trigger = 0, 0
#         for i in range(5):
#             if abs(self.location_data[i][0] - self.location_data[i + 1][0]) > (
#                     self.location_data[i][1] - self.location_data[i + 1][1]):
#                 LR_trigger += 1
#             else:
#                 UD_trigger += 1
#         output = LR_trigger > UD_trigger
#         return output


class Gesture_mode:
    """
    전체 MODE 결정하기 위한 Class
    """
    QUEUE_SIZE = 10

    def __init__(self):
        self.left = [0] * self.QUEUE_SIZE
        self.right = [0] * self.QUEUE_SIZE
        self.left_palm_vector = [[0.] * 3] * self.QUEUE_SIZE
        self.right_palm_vector = [[0.] * 3] * self.QUEUE_SIZE
        self.left_finger_vector = [[0.] * 3] * self.QUEUE_SIZE
        self.right_finger_vector = [[0.] * 3] * self.QUEUE_SIZE

    def __str__(self):
        """
        :return: Monitoring to "string"
        """
        return 'left : {}, right : {}, lpv : {}, lfv : {}, rpv : {}, rfv : {}'.format(
            self.left[-1], self.right[-1],
            self.left_palm_vector[-1], self.left_finger_vector[-1], self.right_palm_vector[-1],
            self.right_finger_vector[-1])

    def update_left(self, left, palm_vector, finger_vector):
        # print(left, 'left')
        self.left.append(left)
        self.left_palm_vector.append(palm_vector)
        self.left_finger_vector.append(finger_vector)
        self.left.pop(0)
        self.left_palm_vector.pop(0)
        self.left_finger_vector.pop(0)

    def update_right(self, right, palm_vector, finger_vector):
        # print(right, 'right')
        self.right.append(right)
        self.right_palm_vector.append(palm_vector)
        self.right_finger_vector.append(finger_vector)
        self.right.pop(0)
        self.right_palm_vector.pop(0)
        self.right_finger_vector.pop(0)

    def select_mode(self, pixel, now_click, now_click2):
        mode = 0
        lpv_mode_1 = [-0.39, 0.144, -0.90]
        lfv_mode_1 = [-0.33, -0.94, 0.]
        rpv_mode_1 = [-0.40, -0.14, -0.9]
        rfv_mode_1 = [-0.33, -0.94, 0.]
        mode_result = 0
        # print(self.left_palm_vector[0], self.left_finger_vector[0],
        # self.right_palm_vector[0], self.right_finger_vector[0])

        # for lpv in self.left_palm_vector:
        #     mode_result = mode_result + get_angle(lpv, lpv_mode_1)
        # for lfv in self.left_finger_vector:
        #     mode_result = mode_result + get_angle(lfv, lfv_mode_1)
        # for rpv in self.right_palm_vector:
        #     mode_result = mode_result + get_angle(rpv, rpv_mode_1)
        # for rfv in self.right_finger_vector:
        #     mode_result = mode_result + get_angle(rfv, rfv_mode_1)

        # 손바닥 펴서 앞에 보여주기
        left_idx_1 = 0
        for left in self.left:
            if left == 6:
                left_idx_1 += 1
        right_idx_1 = 0
        for right in self.right:
            if right == 6:
                right_idx_1 += 1
        if mode_result < 20 and right_idx_1 == 10:
            mode = 1

        # 탈모빔 자세
        left_idx_1 = 0
        for left in self.left:
            if left == 3:
                left_idx_1 += 1
        right_idx_1 = 0
        for right in self.right:
            if right == 3:
                right_idx_1 += 1
        if mode_result < 23 and right_idx_1 == 10:
            mode = 2

        # 손모양 주먹
        left_idx_1 = 0
        for left in self.left:
            if left == 4:
                left_idx_1 += 1
        right_idx_1 = 0
        for right in self.right:
            if right == 1:
                right_idx_1 += 1
        if mode_result < 23 and right_idx_1 == 10:
            pixel.mousemove(now_click, now_click2)
            mode = 3

        # 손모양 사 자세
        left_idx_1 = 0
        for left in self.left:
            if left == 7:
                left_idx_1 += 1
        right_idx_1 = 0
        for right in self.right:
            if right == 7:
                right_idx_1 += 1
        if mode_result < 23 and right_idx_1 == 10:
            mode = 4
        return mode


def get_angle(l1, l2):
    """
    :param l1:
    :param l2:
    :return: 두 벡터 l1, l2 사이의 값 반환 (RADIAN)
    """
    l1_ = np.array([l1[0], l1[1], l1[2]])
    l2_ = np.array([l2[0], l2[1], l2[2]])
    if (norm(l1) * norm(l2)) == 0:
        return 0
    else:
        return np.arccos(np.dot(l1_, l2_) / (norm(l1) * norm(l2)))
    # return np.arccos(np.dot(l1_, l2_) / (norm(l1) * norm(l2)))


def vector_magnitude(one_d_array):
    """
    :param one_d_array: 1D Array
    :return: 크기 반환
    """
    return math.sqrt(np.sum(one_d_array * one_d_array))


def norm(p1):
    """
    :param p1: 점 3차원 정보 list
    :return: 벡터의 크기 반환
    """
    return math.sqrt((p1[0]) ** 2 + (p1[1]) ** 2 + (p1[2]) ** 2)


def convert_offset(x, y):
    """
    :param x: offset input X
    :param y: offset input Y
    :return: Modified x, y coordinates
    """
    return x * 4 / 3 - x_size / 8, y * 4 / 3 - y_size / 8


def inv_convert_off(x, y):
    """
    :param x: offset input X
    :param y: offset input Y
    :return: Inversed x, y coordinates (to unconverted coord)
    """
    return (x + x_size / 8) * 3 / 4, (y + y_size / 8) * 3 / 4


def get_distance(p1, p2, mode='3d'):
    """
    :param p1: Mark_pixel() 객체
    :param p2: Mark_pixel() 객체
    :return: p1과 p2 사이의 거리, 3차원/2차원 mark pixel 모두 거리 반환
    """
    if mode == '3d':
        try:
            return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)
        except:
            return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
    elif mode == '2d':
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


# TODO 프로세스 함수들
def process_static_gesture(array_for_static, value_for_static):
    """
    :param array_for_static: shared array between main process and static gesture detection process
    :param value_for_static: shared value between main process and static gesture detection process
    :return: NO RETURN BUT IT MODIFY SHARED ARR AND VAL
    """
    import keras
    MODEL_STATIC = keras.models.load_model(
        '../keras_util/model_save/my_model_18.h5'
    )

    while True:
        input_ = np.copy(array_for_static[:])
        # print(input_)
        input_ = input_[np.newaxis]
        try:
            prediction = MODEL_STATIC.predict(input_)
            # print(f"predict : {prediction}\n", end='')
            if np.max(prediction[0]) > 0.8:
                value_for_static.value = np.argmax(prediction[0])
                # print(value_for_static.value)
            else:
                value_for_static.value = 0
        except:
            pass


def initialize(array_for_static_l, value_for_static_l, array_for_static_r, value_for_static_r):
    '''
    :param array_for_static_l: static gesture 판별하는 process 와 공유할 왼손 input data
    :param value_for_static_l: static gesture 판별하는 process 와 공유할 왼손 output data
    :param array_for_static_r: static gesture 판별하는 process 와 공유할 오른손 input data
    :param value_for_static_r: static gesture 판별하는 process 와 공유할 오른손 output data
    :return:
    '''

    global MOUSE_USE
    global CLICK_USE
    global WHEEL_USE
    global DRAG_USE
    global pen_color

    app = QtWidgets.QApplication(sys.argv)
    #window = QtWidgets.QWidget()
    ui_load = Load_Ui2()

    # 소리 추가
    import pygame
    pygame.mixer.init()
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    sounds = []
    sounds.append(pygame.mixer.Sound('../sound/writing.wav'))
    sounds.append(pygame.mixer.Sound('../sound/click.wav'))
    sounds.append(pygame.mixer.Sound('../sound/page.wav'))
    sounds.append(pygame.mixer.Sound('../sound/mode1.wav'))
    sounds.append(pygame.mixer.Sound('../sound/mode2.wav'))
    sounds.append(pygame.mixer.Sound('../sound/mode3.wav'))
    sounds.append(pygame.mixer.Sound('../sound/mode4.wav'))
    sounds.append(pygame.mixer.Sound('../sound/ctrlz.wav'))
    sounds.append(pygame.mixer.Sound('../sound/tick.mp3'))
    sounds.append(pygame.mixer.Sound('../sound/window.mp3'))

    # OLD VER.
    # from pygame import mixer
    # mixer.init()
    # mixer.music.load("sound/writing.wav")

    def mode_2_pre(palm, finger, left, p_check):
        palm_th = np.array([-0.41607399, -0.20192736, 0.88662719])
        finger_th = np.array([-0.08736683, -0.96164491, -0.26001175])
        # print(ctrl_z_check, left)
        parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
        if p_check == 0 and left == 3 and parameter < 1.2:
            print('이전 페이지 (Left Arrow)')

            sound = sounds[2]
            sound.play()

            win32api.keybd_event(0x25, 0, 0, 0)  # Left Arrow 누르기.
            win32api.keybd_event(0x25, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.1)
            return 15
        elif p_check > 0:
            return p_check - 1
        else:
            return 0

    def mode_2_laser(state, num, right):
        LASER_CHANGE_TIME = 6
        # print(state, num, right)
        if right:
            num = max(num + 1, 0)
        else:
            num = min(num - 1, LASER_CHANGE_TIME)

        if not state and num > LASER_CHANGE_TIME and right:
            # state = True
            win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
            win32api.keybd_event(0x4C, 0, 0, 0)  # L 누르기.
            win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x4C, 0, win32con.KEYEVENTF_KEYUP, 0)
            state = True
            return state, num
        elif state and num < - 2 and not right:
            # state = False
            win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
            win32api.keybd_event(0x4C, 0, 0, 0)  # L 누르기.
            win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x4C, 0, win32con.KEYEVENTF_KEYUP, 0)
            state = False
            return state, num
        return state, num

    def mode_3_interrupt(mode_global):
        global now_click
        if mode_global == 3:
            # win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
            # win32api.keybd_event(0x31, 0, 0, 0)  # 1 누르기.
            # time.sleep(0.1)
            # win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
            # win32api.keybd_event(0x31, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x1B, 0, 0, 0)  # ESC DOWN
            win32api.keybd_event(0x1B, 0, win32con.KEYEVENTF_KEYUP, 0)  # ESC UP
            print('drag off')
            pos = win32api.GetCursorPos()
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, pos[0], pos[1], 0, 0)
            # ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
            now_click = False

            sound = sounds[0]
            # mixer.music.stop()
            sound.stop()


    def mode_2_off(mode_before, laser_state):
        """
        :param mode_before:
        :param laser_state:
        :return: mode 2 끝날때 레이저 켜져있으면 꺼주기
        """
        if mode_before == 2 and laser_state:
            win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
            win32api.keybd_event(0x4C, 0, 0, 0)  # L 누르기.
            win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x4C, 0, win32con.KEYEVENTF_KEYUP, 0)
            return False

    def mode_3_ctrl_z(palm, finger, left, ctrl_z_check):
        palm_th = np.array([-0.41607399, -0.20192736, 0.88662719])
        finger_th = np.array([-0.08736683, -0.96164491, -0.26001175])
        # print(ctrl_z_check, left)
        parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
        # print(parameter)
        if ctrl_z_check == 0 and left == 6 and parameter < 3.5:
            print('되돌리기 (CTRL + Z)')
            sound = sounds[7]
            sound.play()
            win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
            win32api.keybd_event(0x5a, 0, 0, 0)  # Z 누르기.
            time.sleep(0.1)
            win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x5a, 0, win32con.KEYEVENTF_KEYUP, 0)
            # 최소 N 프레임마다 Control + Z 상황과 가까운지 확인
            return 15
        elif ctrl_z_check > 0:
            return ctrl_z_check - 1
        else:
            return 0

    # def mode_3_ctrl_z2(palm, finger, right, ctrl_z_check):
    #     palm_th = np.array([-0.41607399, -0.20192736, 0.88662719])
    #     finger_th = np.array([-0.08736683, -0.96164491, -0.26001175])
    #     # print(ctrl_z_check, left)
    #     parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
    #     # print(parameter)
    #     if ctrl_z_check == 0 and left == 6 and parameter < 3.5:
    #         print('되돌리기 (CTRL + Z)')
    #         sound = sounds[7]
    #         sound.play()
    #         win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
    #         win32api.keybd_event(0x5a, 0, 0, 0)  # Z 누르기.
    #         time.sleep(0.1)
    #         win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
    #         win32api.keybd_event(0x5a, 0, win32con.KEYEVENTF_KEYUP, 0)
    #         # 최소 N 프레임마다 Control + Z 상황과 가까운지 확인
    #         return 15
    #     elif ctrl_z_check > 0:
    #         return ctrl_z_check - 1
    #     else:
    #         return 0

    def mode_3_ctrl_z2(palm, finger, right, p_check):
        palm_th = np.array([-0.41607399, -0.20192736, 0.88662719])
        finger_th = np.array([-0.08736683, -0.96164491, -0.26001175])
        # print(ctrl_z_check, left)
        parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
        if p_check == 0 and right == 1 and parameter < 1.2:
            print('되돌리기 (CTRL + Z)')
            sound = sounds[7]
            sound.play()

            win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
            win32api.keybd_event(0x5a, 0, 0, 0)  # Z 누르기.
            time.sleep(0.1)
            win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(0x5a, 0, win32con.KEYEVENTF_KEYUP, 0)
            # 최소 N 프레임마다 Control + Z 상황과 가까운지 확인
            return 15
        elif p_check > 0:
            return p_check - 1
        else:
            return 0

    def mode_3_remove_all(palm, finger, left, remove_check):
        # 60 means 60 frames to trigger 'REMOVE ALL'
        REMOVE_THRESHOLD = 60
        palm_th = np.array([-0.41607399, -0.20192736, 0.88662719])
        finger_th = np.array([-0.08736683, -0.96164491, -0.26001175])
        # print(ctrl_z_check, left)
        parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
        if left == 3 and parameter < 2 and remove_check < REMOVE_THRESHOLD:
            return remove_check + 1
        elif remove_check == REMOVE_THRESHOLD:
            # N 프레임 쌓이면 전체 지움
            print('Remove all (E)')
            win32api.keybd_event(0x45, 0, 0, 0)  # E 누르기.
            time.sleep(0.03)
            win32api.keybd_event(0x45, 0, win32con.KEYEVENTF_KEYUP, 0)
            return 0
        else:
            return max(0, remove_check - 1)

    def mode_3_remove_all2(palm, finger, right, remove_check):
        # 60 means 60 frames to trigger 'REMOVE ALL'
        REMOVE_THRESHOLD = 60
        palm_th = np.array([-0.41607399, -0.20192736, 0.88662719])
        finger_th = np.array([-0.08736683, -0.96164491, -0.26001175])
        # print(ctrl_z_check, left)
        parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
        if right == 1 and parameter < 1.2 and remove_check < REMOVE_THRESHOLD:
            return remove_check + 1
        elif remove_check == REMOVE_THRESHOLD:
            # N 프레임 쌓이면 전체 지움
            print('Remove all (E)')
            win32api.keybd_event(0x45, 0, 0, 0)  # E 누르기.
            time.sleep(0.03)
            win32api.keybd_event(0x45, 0, win32con.KEYEVENTF_KEYUP, 0)
            return 0
        else:
            return max(0, remove_check - 1)

    def mode_3_board(palm, finger, left, remove_check):
        # 60 means 60 frames to trigger 'REMOVE ALL'
        REMOVE_THRESHOLD = 30
        palm_th = np.array([-0.15196232, 0.23579129, -0.9598489])
        finger_th = np.array([-0.36294722, -0.91659405, -0.16770409])
        global BOARD_COLOR

        # print(ctrl_z_check, left)
        parameter = get_angle(palm, palm_th) + get_angle(finger, finger_th)
        if left == 7 and parameter < 1 and remove_check < REMOVE_THRESHOLD:
            return remove_check + 1
        elif remove_check == REMOVE_THRESHOLD:
            # N 프레임 쌓이면 전체 지움
            if BOARD_COLOR == 'b':
                print('BOARD ON (K)')
                win32api.keybd_event(0x4B, 0, 0, 0)  # K 누르기.
                time.sleep(0.03)
                win32api.keybd_event(0x4B, 0, win32con.KEYEVENTF_KEYUP, 0)
                return 0
            elif BOARD_COLOR == 'w':
                print('BOARD ON (W)')
                win32api.keybd_event(0x57, 0, 0, 0)  # W 누르기.
                time.sleep(0.03)
                win32api.keybd_event(0x57, 0, win32con.KEYEVENTF_KEYUP, 0)
                return 0
        else:
            return 0


    class Opcv(QThread):

        change_pixmap_signal = pyqtSignal(np.ndarray)
        mode_signal = pyqtSignal(int)

        R = np.array([0.22, -0.98, 0])
        G = np.array([0.73, -0.68, 0])
        B = np.array([0.95, -0.3, 0])
        O = np.array([0.9, 0.4, 0])
        COLOR_SET = {'R': R, 'G': G, 'B': B, 'O': O}

        BASE_LAYER = Image.open('../image/background.png')
        R_LAYER = './image/Red.png'
        G_LAYER = './image/Green.png'
        B_LAYER = './image/Blue.png'
        O_LAYER = './image/Orange.png'
        LAYER_PATH = {'R': R_LAYER, 'G': G_LAYER, 'B': B_LAYER, 'O': O_LAYER}
        LAYER_SET = {'R': Image.open(R_LAYER), 'G': Image.open(G_LAYER),
                     'B': Image.open(B_LAYER), 'O': Image.open(O_LAYER)}

        def __init__(self):
            super().__init__()

        def mode_3_pen_color(self, palm, finger, image):
            global pen_color

            palm_standard = [-0.29779509, -0.56894808, 0.76656126]
            if get_angle(palm, palm_standard) < 0.8:
                color_value = self.COLOR_SET.copy()

                pill_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

                for key, value in self.COLOR_SET.items():
                    color_value[key] = get_angle(finger, value)
                if min(color_value.values()) < 0.6:
                    color_name_l = [k for k, v in color_value.items() if min(color_value.values()) == v]
                    if len(color_name_l) > 0:
                        color_name = color_name_l[0]
                        pill_image.paste(self.LAYER_SET[color_name], (0, 280), mask=self.LAYER_SET[color_name])
                    if color_name != pen_color:
                        sound = sounds[8]
                        sound.play()
                        if color_name == 'R':
                            win32api.keybd_event(0x52, 0, 0, 0)
                            win32api.keybd_event(0x52, 0, win32con.KEYEVENTF_KEYUP, 0)
                        if color_name == 'G':
                            win32api.keybd_event(0x47, 0, 0, 0)
                            win32api.keybd_event(0x47, 0, win32con.KEYEVENTF_KEYUP, 0)
                        if color_name == 'B':
                            win32api.keybd_event(0x42, 0, 0, 0)
                            win32api.keybd_event(0x42, 0, win32con.KEYEVENTF_KEYUP, 0)
                        if color_name == 'O':
                            win32api.keybd_event(0x4F, 0, 0, 0)
                            win32api.keybd_event(0x4F, 0, win32con.KEYEVENTF_KEYUP, 0)
                    pen_color = color_name

                else:
                    pill_image.paste(self.BASE_LAYER, (0, 280), self.BASE_LAYER)

                image = cv2.cvtColor(np.array(pill_image), cv2.COLOR_RGB2BGR)

            return image

            # Color Set : R G B O
            # print(get_angle(finger, finger_vector_1), get_angle(finger, finger_vector_2))

        @pyqtSlot(int, int)
        def mode_setting(self, mode, mode_before):  # 1
            global MOUSE_USE, CLICK_USE, DRAG_USE, WHEEL_USE, mode_global, laser_state
            if mode != mode_before:
                self.mode_signal.emit(int(mode - 1))  # 2 / #2-4

                if mode == 1 and mode_global != mode:
                    MOUSE_USE = False
                    CLICK_USE = False
                    DRAG_USE = False
                    WHEEL_USE = False
                    laser_state = mode_2_off(mode_global, laser_state)
                    print('MODE 1, 대기 모드')
                    sound = sounds[3]
                    sound.play()
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 100, 100, 0, 0)

                    # win32api.keybd_event(0x74, 0, 0, 0)  # F5 DOWN
                    # win32api.keybd_event(0x74, 0, win32con.KEYEVENTF_KEYUP, 0)  # F5 UP

                    mode_3_interrupt(mode_global)

                    mode_global = mode

                if mode == 2 and mode_global != mode:
                    MOUSE_USE = True
                    CLICK_USE = True
                    DRAG_USE = False
                    WHEEL_USE = False

                    mode_3_interrupt(mode_global)

                    print('MODE 2, 기본 발표 모드')
                    sound = sounds[4]
                    sound.play()

                    mode_global = mode

                if mode == 3 and mode_global != mode:
                    MOUSE_USE = True
                    CLICK_USE = False
                    DRAG_USE = True
                    WHEEL_USE = False
                    laser_state = mode_2_off(mode_global, laser_state)
                    # print(mod_cursor_position(200, 200))
                    win32api.SetCursorPos((-1920 + 200, 200))
                    time.sleep(0.1)

                    win32api.keybd_event(0xa2, 0, 0, 0)  # LEFT CTRL 누르기.
                    win32api.keybd_event(0x32, 0, 0, 0)  # 2 누르기.
                    time.sleep(0.1)
                    win32api.keybd_event(0xa2, 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(0x32, 0, win32con.KEYEVENTF_KEYUP, 0)
                    print('MODE 3, 필기 발표 모드')  # 3, # 2-5
                    sound = sounds[5]
                    sound.play()
                    mode_global = mode

                if mode == 4 and mode_global != mode:
                    MOUSE_USE = True
                    CLICK_USE = True
                    DRAG_USE = True
                    WHEEL_USE = True
                    laser_state = mode_2_off(mode_global, laser_state)
                    print('MODE 4, 웹서핑 발표 모드')
                    sound = sounds[6]
                    sound.play()
                    mode_3_interrupt(mode_global)
                    mode_global = mode

        @pyqtSlot(bool)
        def send_img(self, bool_state):  # p를 보는 emit 함수

            sound = sounds[9]
            sound.play()

            # ui.label_6.setPixmap(QtGui.QPixmap("./icon1.png"))
            # Grabber.label_6.setStyleSheet("background-color : white; border-radius: 100px;", )
            # Grabber.label_6.setPixmap(image)
            self.capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap = self.capture
            # For webcam input:
            hands = mp_hands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.7)
            # pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5, upper_body_only=True)

            global width, height, static_gesture_num_l

            # TODO landmark 를 대응 인스턴스로 저장
            class Mark_pixel:
                def __init__(self, x, y, z=0, LR=0):
                    self.x = x
                    self.y = y
                    self.z = z
                    self.LR = LR

                def __str__(self):
                    return str(self.x) + '   ' + str(self.y) + '   ' + str(self.z)

                def to_list(self):
                    """
                    :return: converted mark_pixel to list
                    """
                    return [self.x, self.y, self.z]

                def to_pixel(self):
                    global x_size
                    global y_size
                    return Mark_2d(self.x * x_size, self.y * y_size)

                def __sub__(self, other):
                    return self.x - other.x, self.y - other.y, self.z - other.z

            class Mark_2d:
                def __init__(self, x, y):
                    self.x = x
                    self.y = y

                def __str__(self):
                    return tuple(self.x, self.y)

                @staticmethod
                def mod_cursor_position(pos: tuple):
                    """
                    :param pos: position data (tuple)
                    :return: modified cursor position x, y (tuple)
                    """
                    x, y = pos[0], pos[1]
                    FULLSIZE = 1920, 1080
                    MOD_SIZE = 1600, 640
                    INPUT_SIZE = 1366, 768
                    RATIO = FULLSIZE[0] / INPUT_SIZE[0], FULLSIZE[1] / INPUT_SIZE[1]

                    mod_x = (x * FULLSIZE[0] / MOD_SIZE[0] - (FULLSIZE[0] - MOD_SIZE[0]) / 2) * RATIO[0]
                    mod_x = max(0, mod_x)
                    mod_x = min(FULLSIZE[0], mod_x)
                    mod_y = (y * FULLSIZE[1] / MOD_SIZE[1] - (FULLSIZE[1] - MOD_SIZE[1]) / 2) * RATIO[1]
                    mod_y = max(0, mod_y)
                    mod_y = min(FULLSIZE[1], mod_y)
                    # print(f"{x, y}  >>>  {mod_x, mod_y}")
                    # print(mod_x, mod_y)
                    # 모니터 수, 화면 갯수별로 다르게 Return 해야함

                    if LEFT:
                        return (int(1920 - mod_x) - 1919), int(mod_y)
                    else:
                        return int(mod_x) - 1919, int(mod_y)

                def mousemove(self, now_click, now_click2):

                    cursor_position = (int(self.x), int(self.y))
                    m_cursor_position = self.mod_cursor_position(cursor_position)

                    if now_click == True:
                        cv2.circle(image, (int(self.x * 1.406 / 3), int(self.y * 1.406 / 2.25)), 5, (100, 150, 255), -1)
                    else:
                        cv2.circle(image, (int(self.x * 1.406 / 3), int(self.y * 1.406 / 2.25)), 5, (255, 255, 0), -1)

                    if now_click2 == True:
                        cv2.circle(image, (int(self.x * 1.406 / 3), int(self.y * 1.406 / 2.25)), 5, (255, 110, 0), -1)
                    else:
                        cv2.circle(image, (int(self.x * 1.406 / 3), int(self.y * 1.406 / 2.25)), 5, (255, 255, 0), -1)

                    # self.x, self.y = convert_offset(self.x, self.y)

                    # print(m_cursor_position)
                    win32api.SetCursorPos(m_cursor_position)

                def wheel_up(self):
                    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 200, 200, 30, 1)

                def wheel_down(self):
                    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 200, 200, -30, 1)

                def wheel(self, before):
                    if self.y > before.y:
                        self.wheel_up()
                        print('wheel_up')
                    if self.y < before.y:
                        self.wheel_down()
                        print('wheel_down')

            # def get_center(p1, p2):
            #     return Mark_pixel((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, (p1.z + p2.z) / 2)

            def hand_drag(landmark, now_click):
                """
                :param landmark: landmark or mark_p
                :return: nothing, but it change mouse position and click statement
                """
                global straight_line, rectangular, circle
                # print(now_click, straight_line, rectangular, circle)
                drag_threshold = 1
                if straight_line or rectangular or circle:
                    drag_threshold = drag_threshold * 1.3

                # print(get_distance(landmark[4], landmark[8], mode='3d') < drag_threshold * get_distance(landmark[4],
                #                                                                                      landmark[3],
                #                                                                                      mode='3d'),
                #       now_click)

                if get_distance(landmark[4], landmark[8], mode='3d') < drag_threshold * get_distance(landmark[4],
                                                                                                     landmark[3],
                                                                                                     mode='3d') \
                        and now_click == False:
                    print('drag on')
                    pos = win32api.GetCursorPos()
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, pos[0], pos[1], 0, 0)
                    # ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    now_click = True

                    # mixer.music.play(-1)

                elif get_distance(landmark[4], landmark[8], mode='3d') > drag_threshold * get_distance(landmark[4],
                                                                                                       landmark[3],
                                                                                                       mode='3d') \
                        and now_click == True:
                    print('drag off')
                    pos = win32api.GetCursorPos()
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, pos[0], pos[1], 0, 0)
                    # ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                    now_click = False

                    # mixer.music.stop()

                return now_click

            def hand_drag2(landmark, gesture, now_click):  # 1 : non_click, 13 : click
                """
                :param landmark: landmark or mark_p
                :return: nothing, but it change mouse position and click statement
                """

                # global straight_line, rectangular, circle
                sound = sounds[0]

                # print(gesture)

                if gesture == 13 and now_click == False:
                    print('drag on')
                    pos = win32api.GetCursorPos()
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, pos[0], pos[1], 0, 0)
                    # ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    now_click = True

                    # mixer.music.play(-1)

                    sound.play(-1)

                elif (gesture == 1 or gesture == 6 or gesture == 11) and now_click == True:
                    print('drag off')
                    pos = win32api.GetCursorPos()
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, pos[0], pos[1], 0, 0)
                    # ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                    now_click = False

                    # mixer.music.stop()
                    sound.stop()

                return now_click

            def hand_click(landmark, pixel, HM, now_click2):

                palm_v = HM.palm_vector
                click_angle = get_angle(palm_v, np.array([0, 0, -1]))

                if get_distance(landmark[4], landmark[10]) < get_distance(landmark[7],
                                                                          landmark[8]) and now_click2 == False \
                        and click_angle < 1:
                    print('click')

                    sound = sounds[1]
                    sound.play()
                    pos = win32api.GetCursorPos()
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, pos[0], pos[1], 0, 0)
                    # print(pos)
                    print('click off')
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, pos[0], pos[1], 0, 0)
                    now_click2 = True
                    return -1, now_click2
                if get_distance(landmark[4], landmark[10]) > get_distance(landmark[7],
                                                                          landmark[8]) and now_click2 == True:
                    now_click2 = False

                return 0, now_click2

            """
            def blurFunction(src):
                with mp_face_detection.FaceDetection(
                        min_detection_confidence=0.5) as face_detection:  
                    "with 문, mp_face_detection.FaceDetection 클래스를 face_detection 으로 사용"
                    image = cv2.cvtColor(src, cv2.COLOR_BGR2RGB)  # image 파일의 BGR 색상 베이스를 RGB 베이스로 바꾸기
                    results = face_detection.process(image)  # 튜플 형태
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    image_rows, image_cols, _ = image.shape
                    c_mask: np.ndarray = np.zeros((image_rows, image_cols), np.uint8)
                    if results.detections:
                        for detection in results.detections:
                            if not detection.location_data:
                                break
                            if image.shape[2] != 3:
                                raise ValueError('Input image must contain three channel rgb data.')
                            location = detection.location_data
                            if location.format != location_data_pb2.LocationData.RELATIVE_BOUNDING_BOX:
                                raise ValueError('LocationData must be relative for this drawing funtion to work.')
                            # Draws bounding box if exists.
                            if not location.HasField('relative_bounding_box'):
                                break
                            relative_bounding_box = location.relative_bounding_box
                            rect_start_point = mp_drawing._normalized_to_pixel_coordinates(
                                relative_bounding_box.xmin, relative_bounding_box.ymin, image_cols,
                                image_rows)
                            rect_end_point = mp_drawing._normalized_to_pixel_coordinates(
                                relative_bounding_box.xmin + relative_bounding_box.width,
                                relative_bounding_box.ymin + +relative_bounding_box.height, image_cols,
                                image_rows)
                            try:
                                x1 = int((rect_start_point[0] + rect_end_point[0]) / 2)
                                y1 = int((rect_start_point[1] + rect_end_point[1]) / 2)
                                a = int(rect_end_point[0] - rect_start_point[0])
                                b = int(rect_end_point[1] - rect_start_point[1])
                                radius = int(math.sqrt(a * a + b * b) / 2 * 0.7)
                                # 원 스펙 설정
                                cv2.circle(c_mask, (x1, y1), radius, (255, 255, 255), -1)
                            except:
                                pass
                        img_all_blurred = cv2.blur(image, (17, 17))
                        c_mask = cv2.cvtColor(c_mask, cv2.COLOR_GRAY2BGR)
                        # print(c_mask.shape)
                        image = np.where(c_mask > 0, img_all_blurred, image)
                return image
            """
            before_c = Mark_pixel(0, 0, 0)
            pixel_c = Mark_pixel(0, 0, 0)
            hm_idx = False
            finger_open_ = [False for _ in range(5)]
            gesture_time = time.time()
            # gesture = Gesture()
            gesture_mode = Gesture_mode()

            ctrl_z_check_number = 0
            remove_all_number = 0
            board_num = 0
            p_check_number = 0

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            before_time = time.time()

            click_tr = 0
            mode_before = 0
            p_key_ready = False
            mode = 0
            global gesture_check
            global mode_global
            global straight_line
            global rectangular
            global circle

            global laser_num, laser_state




            print('loaded')

            if ui_load.status == 0:
                ui_load.close()
                ui_load.status = 1

            now_click = False
            now_click2 = False


            HM = Handmark()

            import random

            if VISUALIZE_GRAPH:
                fig = plt.figure(figsize=(10, 6))  # figure(도표) 생성
                fig.canvas.set_window_title('Hand Vector Visualization Ver 1')
                fig.suptitle('Hand Vector Visualization Ver 1', fontweight="bold")

                plt.rcParams['axes.grid'] = True
                plt.rcParams["figure.figsize"] = (10, 4)

                leftPalmSubplot = plt.subplot(221, xlim=(0, 50), ylim=(-1, 1))
                leftFingerSubplot = plt.subplot(223, xlim=(0, 50), ylim=(-1, 1))
                rightPalmSubplot = plt.subplot(222, xlim=(0, 50), ylim=(-1, 1))
                rightFingerSubplot = plt.subplot(224, xlim=(0, 50), ylim=(-1, 1))

                plt.subplots_adjust(left=0.125, bottom=0.1, right=0.9, top=0.9, wspace=0.2, hspace=0.6)

                leftPalmSubplot.set_title('Left Palm Vector')
                leftFingerSubplot.set_title('Left Finger Vector')
                leftPalmSubplot.set_xlabel('time')
                leftPalmSubplot.set_ylabel('value')
                leftFingerSubplot.set_xlabel('time')
                leftFingerSubplot.set_ylabel('value')
                rightPalmSubplot.set_title('Right Palm Vector')
                rightFingerSubplot.set_title('Right Finger Vector')
                rightPalmSubplot.set_xlabel('time')
                rightPalmSubplot.set_ylabel('value')
                rightFingerSubplot.set_xlabel('time')
                rightFingerSubplot.set_ylabel('value')

                max_points = 50

                lineLP, = leftPalmSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='blue', ms=1)
                lineLP2, = leftPalmSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='red', ms=1)
                lineLP3, = leftPalmSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='green', ms=1)
                lineLF, = leftFingerSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='blue', ms=1)
                lineLF2, = leftFingerSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='red', ms=1)
                lineLF3, = leftFingerSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='green', ms=1)
                lineRP, = rightPalmSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='blue', ms=1)
                lineRP2, = rightPalmSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='red', ms=1)
                lineRP3, = rightPalmSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='green', ms=1)
                lineRF, = rightFingerSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='blue', ms=1)
                lineRF2, = rightFingerSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='red', ms=1)
                lineRF3, = rightFingerSubplot.plot(np.arange(max_points),
                                np.ones(max_points, dtype=np.float) * np.nan, lw=1, c='green', ms=1)


                def initLP():
                    return lineLP, lineLP2, lineLP3

                def initLF():
                    return lineLF, lineLF2, lineLF3

                def initRP():
                    return lineRP, lineRP2, lineRP3

                def initRF():
                    return lineRF, lineRF2, lineRF3

                def animateLP(i):
                    y = gesture_mode.left_palm_vector[-1][0]
                    old_y = lineLP.get_ydata()
                    new_y = np.r_[old_y[1:], y]
                    lineLP.set_ydata(new_y)

                    y2 = gesture_mode.left_palm_vector[-1][1]
                    old_y2 = lineLP2.get_ydata()
                    new_y2 = np.r_[old_y2[1:], y2]
                    lineLP2.set_ydata(new_y2)

                    y3 = gesture_mode.left_palm_vector[-1][2]
                    old_y3 = lineLP3.get_ydata()
                    new_y3 = np.r_[old_y3[1:], y3]
                    lineLP3.set_ydata(new_y3)
                    # print(new_y)
                    return lineLP, lineLP2, lineLP3

                def animateLF(i):
                    y = gesture_mode.left_finger_vector[-1][0]
                    old_y = lineLF.get_ydata()
                    new_y = np.r_[old_y[1:], y]
                    lineLF.set_ydata(new_y)

                    y2 = gesture_mode.left_finger_vector[-1][1]
                    old_y2 = lineLF2.get_ydata()
                    new_y2 = np.r_[old_y2[1:], y2]
                    lineLF2.set_ydata(new_y2)

                    y3 = gesture_mode.left_finger_vector[-1][2]
                    old_y3 = lineLF3.get_ydata()
                    new_y3 = np.r_[old_y3[1:], y3]
                    lineLF3.set_ydata(new_y3)
                    # print(new_y)
                    return lineLF, lineLF2, lineLF3

                def animateRP(i):
                    y = gesture_mode.right_palm_vector[-1][0]
                    old_y = lineRP.get_ydata()
                    new_y = np.r_[old_y[1:], y]
                    lineRP.set_ydata(new_y)

                    y2 = gesture_mode.right_palm_vector[-1][1]
                    old_y2 = lineRP2.get_ydata()
                    new_y2 = np.r_[old_y2[1:], y2]
                    lineRP2.set_ydata(new_y2)

                    y3 = gesture_mode.right_palm_vector[-1][2]
                    old_y3 = lineRP3.get_ydata()
                    new_y3 = np.r_[old_y3[1:], y3]
                    lineRP3.set_ydata(new_y3)
                    # print(new_y)
                    return lineRP, lineRP2, lineRP3

                def animateRF(i):
                    y = gesture_mode.right_finger_vector[-1][0]
                    old_y = lineRF.get_ydata()
                    new_y = np.r_[old_y[1:], y]
                    lineRF.set_ydata(new_y)

                    y2 = gesture_mode.right_finger_vector[-1][1]
                    old_y2 = lineRF2.get_ydata()
                    new_y2 = np.r_[old_y2[1:], y2]
                    lineRF2.set_ydata(new_y2)

                    y3 = gesture_mode.right_finger_vector[-1][2]
                    old_y3 = lineRF3.get_ydata()
                    new_y3 = np.r_[old_y3[1:], y3]
                    lineRF3.set_ydata(new_y3)
                    # print(new_y)
                    return lineRF, lineRF2, lineRF3

                animLP = animation.FuncAnimation(fig, animateLP, init_func=initLP, frames=200, interval=50, blit=False)
                animLF = animation.FuncAnimation(fig, animateLF, init_func=initLF, frames=200, interval=50, blit=False)
                animRP = animation.FuncAnimation(fig, animateRP, init_func=initRP, frames=200, interval=50, blit=False)
                animRF = animation.FuncAnimation(fig, animateRF, init_func=initRF, frames=200, interval=50, blit=False)

                plt.legend([lineLP, lineLP2, lineLP3], ["X", "Y", "Z"], loc="lower left")
                plt.show()

            if not cap.isOpened():
                raise IOError



            while bool_state and cap.isOpened():
                # print('cam')


                success, image = cap.read()

                if not success:
                    print("Ignoring empty camera frame.")
                    # If loading a video, use 'break' instead of 'continue'.
                    break

                # Flip the image horizontally for a later selfie-view display, and convert
                # the BGR image to RGB.
                if not LEFT :
                    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                else:
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


                image.flags.writeable = False
                results = hands.process(image)
                # Draw the hand annotations on the image.
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # 손!!
                if results.multi_hand_landmarks:
                    multi_hand = len(results.multi_hand_landmarks)
                    mark_p_list = []

                    for hand_landmarks in results.multi_hand_landmarks:
                        '''hand_landmarks 는 감지된 손의 갯수만큼의 원소 수를 가진 list 자료구조'''
                        mark_p = []
                        mp_drawing.draw_landmarks(
                            image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                        for i in range(21):
                            mark_p.append(Mark_pixel(hand_landmarks.landmark[i].x, hand_landmarks.landmark[i].y,
                                                     hand_landmarks.landmark[i].z))
                        mark_p_list.append(mark_p)

                    for i in range(len(mark_p_list)):  # for 문 한 번 도는게 한 손에 대한 것임
                        LR_idx = results.multi_handedness[i].classification[0].label
                        # LR_idx = LR_idx[:-1]
                        # print(LR_idx)
                        if LR_idx[0] == 'R':
                            image = cv2.putText(image, 'V', (
                                int(mark_p_list[i][17].x * image.shape[1]), int(mark_p_list[i][17].y * image.shape[0])),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)

                        # sd_check = np.array(mark_p_list)
                        # print(np.std(sd_check))

                        mark_p_list[i].append(LR_idx)

                        mark_p = mark_p_list[i]
                        # print(len(mark_p_list), i)
                        # Handmark 정보 입력
                        # print(mark_p[-1], " / ", mark_p[0])

                        if len(mark_p) == 22 and hm_idx == False:
                            HM.p_list = mark_p
                            hm_idx = True
                        # print(HM.p_list[-1])
                        # palm_vector 저장
                        palm_vector = HM.get_palm_vector()
                        finger_vector = HM.get_finger_vector()

                        # mark_p 입력
                        if hm_idx:
                            HM.p_list = mark_p
                            # mark_p[-1] = mark_p[-1][:-1]
                            if USE_TENSORFLOW:
                                # print(len(HM.p_list[-1]))
                                if len(mark_p[-1]) == 4:
                                    f_p_list = HM.return_18_info()
                                    array_for_static_l[:] = f_p_list
                                    # print(array_for_static)
                                    static_gesture_num_l = value_for_static_l.value
                                if len(mark_p[-1]) == 5:
                                    f_p_list = HM.return_18_info()
                                    array_for_static_r[:] = f_p_list
                                    # print(array_for_static)
                                    static_gesture_num_r = value_for_static_r.value

                                # try:
                                #     static_gesture_drawing(static_gesture_num, mark_p[-1])
                                # except:
                                #     print('static_drawing error')
                                # print(static_gesture_num)
                            else:
                                finger_open_for_ml = np.ndarray.tolist(HM.return_finger_state())
                                # 정지 제스쳐 확인
                                # static_gesture_detect(finger_open_for_ml, mark_p[-1])
                            finger_open_ = HM.return_finger_state()

                        mark_p0 = mark_p[0].to_pixel()
                        mark_p5 = mark_p[5].to_pixel()

                        swipe_signal = False
                        # pixel_c = mark_c.to_pixel()
                        if len(mark_p[-1]) == 5:
                            palm_vector = HM.get_palm_vector()
                            finger_vector = HM.get_finger_vector()

                            if finger_open_[1] == 1 and \
                                    sum(finger_open_[3:]) == 0 and \
                                    finger_open_[2] == 1 and \
                                    get_angle(mark_p[5] - mark_p[8], mark_p[5] - mark_p[12]) < 0.3:
                                swipe_signal = True  # swipe signal
                                # print('swipe')

                            if mode_global == 2:
                                # MODE 2 LEFT ARROW
                                p_check_number = mode_2_pre(palm_vector, finger_vector,
                                                            static_gesture_num_r, p_check_number)
                                # MODE 2 LASER POINTER
                                laser_hand = np.all(finger_open_ == np.array([1, 1, 1, 0, 0]))
                                laser_state, laser_num = mode_2_laser(laser_state, laser_num, laser_hand)

                            # MODE 3 CTRL + Z
                            if mode_global == 3:
                                # ctrl_z_check_number = mode_3_ctrl_z(palm_vector, finger_vector,
                                #                                     static_gesture_num_r, ctrl_z_check_number)
                                # remove_all_number = mode_3_remove_all(palm_vector, finger_vector,
                                #                                       static_gesture_num_r, remove_all_number)
                                remove_all_number = mode_3_remove_all2(palm_vector, finger_vector,
                                                                      static_gesture_num_r, remove_all_number)

                                ctrl_z_check_number = mode_3_ctrl_z2(palm_vector, finger_vector,
                                                                    static_gesture_num_r, ctrl_z_check_number)

                                board_num = mode_3_board(palm_vector, finger_vector,
                                                         static_gesture_num_r, board_num)

                            pixel_c = mark_p5
                            # # gesture updating
                            # if len(mark_p) == 22:
                            #     # print(HM.p_list[-1])
                            #     gesture.update(HM, static_gesture_num_r, swipe_signal)
                            #     # print(static_gesture_num)
                            #     try:
                            #         # print(time.time() - gesture_time)
                            #         # LRUD = gesture.gesture_LRUD()
                            #         # print(LRUD)
                            #         # print(gesture.gesture_data)
                            #         # print(6. in gesture.gesture_data)
                            #         if time.time() - gesture_time > 0.5 and USE_DYNAMIC == True:
                            #             # 다이나믹 제스처
                            #             detect_signal = gesture.detect_gesture()
                            #         if detect_signal == -1:  # 디텍트했을때!
                            #             gesture_time = time.time()
                            #             detect_signal = 0
                            #     except:
                            #         pass

                        if len(mark_p[-1]) == 5:
                            gesture_mode.update_right(static_gesture_num_r, palm_vector, finger_vector)

                        # 마우스 움직임, 드래그

                        if mode_global == 3 and len(mark_p[-1]) == 5:
                            # 왼손 오른손 구분 모델이 잘 작동하지 않는 경우 있어 손바닥, 손가락의 벡터를 이용해 추가 검증
                            palm_vector_drag = HM.get_palm_vector()
                            finger_vector_drag = HM.get_finger_vector()
                            # lpv_mode_1 = [-0.39, 0.144, -0.90]
                            # lfv_mode_1 = [-0.33, -0.94, 0.]
                            rpv_mode_1 = [-0.40, -0.14, -0.9]
                            rfv_mode_1 = [-0.33, -0.94, 0.]
                            pv_angle = get_angle(palm_vector_drag, rpv_mode_1)
                            fv_angle = get_angle(finger_vector_drag, rfv_mode_1)
                            # print(f"{pv_angle} /// {fv_angle}")
                            
                            if pv_angle + fv_angle < 3:
                                pixel_c.mousemove(now_click, now_click2)
                                now_click2 = hand_drag2(mark_p, static_gesture_num_r, now_click2)

                        if (get_distance(pixel_c, before_c) < get_distance(mark_p0, mark_p5)) and \
                                sum(finger_open_[3:]) == 0 and \
                                finger_open_[1] == 1 and \
                                len(mark_p[-1]) == 5 and \
                                MOUSE_USE == True and \
                                mode_global != 3:

                            pixel_c.mousemove(now_click, now_click2)

                            # print(click_tr[2])

                            if finger_open_[2] != 1 and click_tr > -1 and DRAG_USE == True:
                                now_click = hand_drag(mark_p, now_click)

                            if finger_open_[2] != 1 and CLICK_USE == True:
                                if not now_click:
                                    click_tr, now_click2 = hand_click(mark_p, pixel_c, HM, now_click2)
                            # else:
                            # win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, int(pixel_c.x), int(pixel_c.y), 0, 0)

                            # 마우스 휠
                            if finger_open_[2] == 1 and WHEEL_USE == True and get_angle(mark_p[5] - mark_p[8],
                                                                                        mark_p[5] - mark_p[12]) < 0.3:
                                pixel_c.wheel(before_c)

                        if len(mark_p[-1]) == 5:
                            mode = gesture_mode.select_mode(pixel_c, now_click, now_click2)
                            if mode != 4 and mode_before != 4 and mode_global:
                                self.mode_setting(mode, mode_before)
                                mode_before = mode

                        # MODE 3 색 변경
                        if len(mark_p[-1]) == 4:
                            gesture_mode.update_left(static_gesture_num_l, palm_vector, finger_vector)

                            # MODE CHANGE
                            palm_vector = HM.get_palm_vector()
                            finger_vector = HM.get_finger_vector()


                            # 입력 모양 모니터링
                            # print(static_gesture_num_l, straight_line, rectangular, circle)

                            # 직선 그리기
                            if mode_global == 3 and static_gesture_num_l == 13:
                                straight_line = True
                                win32api.keybd_event(0xA0, 0, 0, 0)  # LShift 누르기.
                            else:
                                win32api.keybd_event(0xA0, 0, win32con.KEYEVENTF_KEYUP, 0)
                                straight_line = False

                            # 네모 그리기
                            if mode_global == 3 and static_gesture_num_l == 11:
                                rectangular = True
                                win32api.keybd_event(0xA2, 0, 0, 0)  # LCtrl 누르기.
                            else:
                                win32api.keybd_event(0xA2, 0, win32con.KEYEVENTF_KEYUP, 0)
                                rectangular = False

                            # 원 그리기
                            if mode_global == 3 and static_gesture_num_l == 1:
                                circle = True
                                win32api.keybd_event(0x09, 0, 0, 0)  # TAB 누르기.
                            else:
                                win32api.keybd_event(0x09, 0, win32con.KEYEVENTF_KEYUP, 0)
                                circle = False

                            # 펜 색 변경
                            if not now_click:
                                if mode_global == 3 and len(mark_p[-1]) == 4 and static_gesture_num_l == 6:
                                    image = self.mode_3_pen_color(palm_vector, finger_vector, image)

                        before_c = pixel_c
                        if multi_hand != 2 and (straight_line + rectangular + circle):
                            win32api.keybd_event(0xA0, 0, win32con.KEYEVENTF_KEYUP, 0)
                            straight_line = False
                            win32api.keybd_event(0xA2, 0, win32con.KEYEVENTF_KEYUP, 0)
                            rectangular = False
                            win32api.keybd_event(0x09, 0, win32con.KEYEVENTF_KEYUP, 0)
                            circle = False

                FPS = round(1 / (time.time() - before_time), 2)

                before_time = time.time()

                image = cv2.resize(image, (577, 433))
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                if LEFT:
                    image = cv2.flip(image, 1)
                image = cv2.putText(image, str(FPS), (18, 30), cv2.FONT_HERSHEY_DUPLEX, 0.65, (42, 46, 57), 1, cv2.LINE_AA)

                self.change_pixmap_signal.emit(image)
                if cv2.waitKey(5) & 0xFF == 27:
                    print('exitcode : 100')
                    exit()
                    break

            hands.close()
            self.capture.release()

    class Setting_window(QtWidgets.QDialog):
        def setupUi(self, Dialog):
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)  # | QtCore.Qt.WindowStaysOnTopHint)
            self.setWindowIcon((QtGui.QIcon('../icon1.png')))
            global language_setting
            Dialog.setObjectName("Setting")
            Dialog.resize(600, 485)
            Dialog.setFixedSize(600, 485)
            Dialog.setWindowOpacity(0.85)
            if not DARK_MODE: Dialog.setStyleSheet("background-color : rgb(238, 239, 241);");
            else: Dialog.setStyleSheet("background-color : rgb(42, 46, 57);");

            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("../image/icon/setting.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            Dialog.setWindowIcon(icon)

            self.pushButton_ok = QtWidgets.QPushButton(Dialog)
            self.pushButton_ok.setGeometry(QtCore.QRect(30, 356, 261, 100))
            self.pushButton_ok.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 217, 104, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/OK.png);
                }
                QPushButton:hover {
                    background-color: rgb(0, 217, 104); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(0, 217, 104); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            self.pushButton_ok.setObjectName("pushButton_ok")
            self.pushButton_ok.clicked.connect(Dialog.accept)
            self.pushButton_ok.clicked.connect(self.getComboBoxItem)

            self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
            self.pushButton_cancel.setGeometry(QtCore.QRect(310, 356, 261, 100))
            self.pushButton_cancel.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 160, 182, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/Cancel.png);
                }
                QPushButton:hover {
                    background-color: rgb(0, 160, 182); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(0, 160, 182); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            self.pushButton_cancel.setObjectName("pushButton_cancel")
            self.pushButton_cancel.clicked.connect(Dialog.reject)

            font = QtGui.QFont()
            font.setFamily("서울남산 장체B")
            font.setPointSize(18)

            font2 = QtGui.QFont()
            font2.setFamily("서울남산 장체B")
            font2.setPointSize(15)
            self.comboBox = QtWidgets.QComboBox(Dialog)
            self.comboBox.setGeometry(QtCore.QRect(140, 95, 321, 41))
            self.comboBox.setObjectName("comboBox")
            self.comboBox.setFont(font2)
            if language_setting == '한국어(Korean)':
                self.comboBox.addItem("한국어(Korean)")
                self.comboBox.addItem("영어(English)")
            elif language_setting == '영어(English)':
                self.comboBox.addItem("영어(English)")
                self.comboBox.addItem("한국어(Korean)")
            if not DARK_MODE:
                self.comboBox.setStyleSheet("color : rgb(32, 36, 47);")
            else:
                self.comboBox.setStyleSheet("color : rgb(248, 249, 251);")

            self.comboBox2 = QtWidgets.QComboBox(Dialog)
            self.comboBox2.setGeometry(QtCore.QRect(140, 180, 321, 41))
            self.comboBox2.setObjectName("comboBox2")
            self.comboBox2.setFont(font2)
            if DARK_MODE == True:
                self.comboBox2.addItem("다크 모드 (Dark Mode)")
                self.comboBox2.addItem("라이트 모드 (Light Mode)")
            elif DARK_MODE == False:
                self.comboBox2.addItem("라이트 모드 (Light Mode)")
                self.comboBox2.addItem("다크 모드 (Dark Mode)")
            if not DARK_MODE:
                self.comboBox2.setStyleSheet("color : rgb(32, 36, 47);")
            else:
                self.comboBox2.setStyleSheet("color : rgb(248, 249, 251);")

            global LEFT
            self.comboBox3 = QtWidgets.QComboBox(Dialog)
            self.comboBox3.setGeometry(QtCore.QRect(140, 265, 321, 41))
            self.comboBox3.setObjectName("comboBox3")
            self.comboBox3.setFont(font2)
            if LEFT:
                self.comboBox3.addItem("왼손 모드 (Left-hand Mode)")
                self.comboBox3.addItem("오른손 모드 (Right-hand Mode)")
            else:
                self.comboBox3.addItem("오른손 모드 (Right-hand Mode)")
                self.comboBox3.addItem("왼손 모드 (Left-hand Mode)")
            if not DARK_MODE:
                self.comboBox3.setStyleSheet("color : rgb(32, 36, 47);")
            else:
                self.comboBox3.setStyleSheet("color : rgb(248, 249, 251);")

            self.label = QtWidgets.QLabel(Dialog)
            self.label.setGeometry(QtCore.QRect(95, 37, 450, 31))
            self.label.setFont(font)
            self.label.setObjectName("label")

            self.retranslateUi(Dialog)
            QtCore.QMetaObject.connectSlotsByName(Dialog)

        def retranslateUi(self, Dialog):
            _translate = QtCore.QCoreApplication.translate
            Dialog.setWindowTitle(_translate("Setting Window", "Setting Window"))
            self.label.setText(_translate("Dialog", "언어 / 테마 설정 (Language / Theme Setting)"))
            if not DARK_MODE:
                self.label.setStyleSheet("color : rgb(32, 36, 47);")
            else:
                self.label.setStyleSheet("color : rgb(248, 249, 251);")

        def getComboBoxItem(self):
            global language_setting
            global DARK_MODE
            global LEFT
            language = self.comboBox.currentText()
            theme = self.comboBox2.currentText()
            leftright_setting = self.comboBox3.currentText()
            # print(crnttxt)
            # if (theme == 'Dark Mode') != DARK_MODE:
            #     DARK_MODE = (theme == 'Dark Mode')
            #     # ui.setupTheme(ui, theme)
            if language != language_setting or (theme == '다크 모드 (Dark Mode)') != DARK_MODE or ((leftright_setting == "왼손 모드 (Left-hand Mode)") != LEFT):
                DARK_MODE = (theme == '다크 모드 (Dark Mode)')
                language_setting = language
                LEFT = (leftright_setting == "왼손 모드 (Left-hand Mode)")
                # print("Set Language : ", crnttxt)
                ui.setupLanguage(ui, language, DARK_MODE, LEFT)

    class Exit_window(QtWidgets.QDialog):
        def setupUi(self, Dialog):
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)  # | QtCore.Qt.WindowStaysOnTopHint)
            global language_setting
            Dialog.setObjectName("Exit")
            Dialog.resize(600, 400)
            Dialog.setFixedSize(600, 400)
            Dialog.setWindowOpacity(0.85)
            # msgBox.setStyleSheet("background-color:rgba(255, 255, 255, 255);")
            if not DARK_MODE:
                Dialog.setStyleSheet("background-color : rgb(238, 239, 241);");
            else:
                Dialog.setStyleSheet("background-color : rgb(42, 46, 57);");
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("../image/icon/exit.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            Dialog.setWindowIcon(icon)

            self.pushButton_ok = QtWidgets.QPushButton(Dialog)
            self.pushButton_ok.setGeometry(QtCore.QRect(30, 271, 261, 100))
            self.pushButton_ok.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 217, 104, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/OK.png);
                }
                QPushButton:hover {
                    background-color: rgb(0, 217, 104); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(0, 217, 104); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            self.pushButton_ok.setObjectName("pushButton_ok")
            self.pushButton_ok.clicked.connect(Dialog.accept)
            self.pushButton_ok.clicked.connect(self.exitProgram)

            self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
            self.pushButton_cancel.setGeometry(QtCore.QRect(310, 271, 261, 100))
            self.pushButton_cancel.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 160, 182, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/Cancel.png);
                }
                QPushButton:hover {
                    background-color: rgb(0, 160, 182); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(0, 160, 182); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            self.pushButton_cancel.setObjectName("pushButton_cancel")
            self.pushButton_cancel.clicked.connect(Dialog.reject)

            font = QtGui.QFont()
            font.setFamily("서울남산 장체B")
            font.setPointSize(22)
            font2 = QtGui.QFont()
            font2.setFamily("서울남산 장체B")
            font2.setPointSize(15)

            self.label = QtWidgets.QLabel(Dialog)
            self.label.setGeometry(QtCore.QRect(130, 50, 401, 150))
            self.label.setFont(font)
            self.label.setObjectName("label")

            self.exitUi(Dialog)
            QtCore.QMetaObject.connectSlotsByName(Dialog)

        def exitUi(self, Dialog):
            _translate = QtCore.QCoreApplication.translate
            Dialog.setWindowTitle(_translate("Exit?", "Exit?"))
            self.label.setText(_translate("Dialog", "이용해 주셔서 감사합니다! \n \n프로그램을 종료하시겠습니까?"))
            if not DARK_MODE:
                self.label.setStyleSheet("color : rgb(32, 36, 47);");
            else:
                self.label.setStyleSheet("color : rgb(248, 249, 251);");

        def exitProgram(self):
            system("taskkill /f /im ZoomIt64.exe")
            system("taskkill /f /im ZoomIt.exe")
            system("taskkill /f /im Motion-Presentation.exe")

            if EXIT_SURVEY:
                os.system('''../open_survey.bat''')

            sys.exit()

    class Grabber(QtWidgets.QMainWindow):
        click_mode = pyqtSignal(int, int)
        button6_checked = pyqtSignal(bool)

        dirty = True

        def __init__(self):
            super(Grabber, self).__init__()
            # self.showMaximized()
            self.setGeometry(0, 0, 1920, 1080)

            self.setWindowIcon((QtGui.QIcon('../icon1.png')))

            # ensure that the widget always stays on top, no matter what
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)  # | QtCore.Qt.WindowStaysOnTopHint)
            layout = QtWidgets.QVBoxLayout()

            self.setLayout(layout)
            # limit widget AND layout margins
            layout.setGeometry(QtCore.QRect(0, 0, 1328, 147))
            layout.setContentsMargins(0, 0, 0, 0)  # left, top, right, bottom
            self.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # create a "placeholder" widget for the screen grab geometry
            self.grabWidget = QtWidgets.QWidget()
            # self.grabWidget.setGeometry(0, 0, 100, 100)

            layout.addWidget(self.grabWidget)

            # let's add a configuration panel
            self.panel = QtWidgets.QWidget()
            layout.addWidget(self.panel)

            panelLayout = QtWidgets.QHBoxLayout()
            self.panel.setLayout(panelLayout)
            panelLayout.setContentsMargins(0, 0, 0, 0)  # 틀 너비 바꾸는 느낌
            self.setContentsMargins(0, 0, 0, 0)

            # self.configButton = QtWidgets.QPushButton(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon), '')
            # self.configButton.setFlat(True)
            # panelLayout.addWidget(self.configButton)

            # panelLayout.addWidget(VLine())

            # self.fpsSpinBox = QtWidgets.QSpinBox()
            # panelLayout.addWidget(self.fpsSpinBox)
            # self.fpsSpinBox.setRange(1, 50)
            # self.fpsSpinBox.setValue(15)
            # panelLayout.addWidget(QtWidgets.QLabel('fps'))

            # panelLayout.addWidget(VLine())

            self.widthLabel = QtWidgets.QLabel()
            # panelLayout.addWidget(self.widthLabel)
            self.widthLabel.setFrameShape(QtWidgets.QLabel.StyledPanel | QtWidgets.QLabel.Sunken)

            # panelLayout.addWidget(QtWidgets.QLabel('x'))

            self.heightLabel = QtWidgets.QLabel()
            # panelLayout.addWidget(self.heightLabel)
            self.heightLabel.setFrameShape(QtWidgets.QLabel.StyledPanel | QtWidgets.QLabel.Sunken)
            # panelLayout.addWidget(QtWidgets.QLabel('px'))
            #
            # panelLayout.addWidget(VLine())

            # self.recButton = QtWidgets.QPushButton('rec')
            # panelLayout.addWidget(self.recButton)
            #
            # self.playButton = QtWidgets.QPushButton('play')
            # panelLayout.addWidget(self.playButton)

            # panelLayout.addStretch(0)
            # self.loading = Loading()
            # self.loading.setupUi(self)

        def setButtonStyle(self, pushButton):
            pushButton.setStyleSheet(
                '''
                QPushButton{image:url(./image/KOR/2-1.png); border:0px;}
                QPushButton:checked{image:url(./image/KOR/2-2.png); border:0px;}

                ''')
            return pushButton

        def setupUi(self, Form):
            # system("ZoomIt.exe")
            Form.setObjectName("Form")
            Form.resize(1920, 1080)
            self.From_button = False

            if not DARK_MODE: Form.setStyleSheet("background-color : rgb(248, 249, 251);");
            else: Form.setStyleSheet("background-color : rgb(32, 36, 47);");

            ui_load.close()

            self.label = QtWidgets.QLabel('Motion Presentation', Form)
            self.label.setGeometry(QtCore.QRect(198, 49, 213, 34)) #

            if not DARK_MODE: self.label.setStyleSheet("color : rgb(32, 36, 47);");
            else: self.label.setStyleSheet("color : rgb(248, 249, 251);");

            font = QtGui.QFont()
            font.setFamily("서울남산 장체B")
            font.setPointSize(14)
            self.label.setFont(font)


            # self.label.setStyleSheet("image:url(./Image/logo.png)")
            # self.label.setObjectName("label")

            # self.label_2 = QtWidgets.QLabel(Form)
            # self.label_2.setGeometry(QtCore.QRect(30, 100, 341, 41))
            # font = QtGui.QFont()
            # font.setFamily("서울남산 장체B")
            # font.setPointSize(36)
            # self.label_2.setFont(font)
            # self.label_2.setStyleSheet("color : #C4BCB8;")
            # self.label_2.setObjectName("label_2")

            # self.label_3 = QtWidgets.QLabel(Form)
            # self.label_3.setGeometry(QtCore.QRect(373, 88, 56, 41))
            # font = QtGui.QFont()
            # font.setFamily("서울남산 장체B")
            # font.setPointSize(18)
            # self.label_3.setFont(font)
            # self.label_3.setStyleSheet("color : #ACCCC4;")
            # self.label_3.setObjectName("label_3")

            # Button 5 : Power
            self.pushButton_5 = QtWidgets.QPushButton(Form)
            self.pushButton_5.setGeometry(QtCore.QRect(21, 383, 357, 71))
            self.pushButton_5.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(226, 0, 46, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/KOR/cam_on.png);
                }
                QPushButton:hover {
                    background-color: rgb(246, 20, 66); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(246, 20, 66); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            self.pushButton_5.setObjectName("pushButton_5")
            self.pushButton_5.setCheckable(True)
            self.pushButton_5.raise_()

            # Button 6 : Guide Open
            self.pushButton_6 = QtWidgets.QPushButton(Form)
            self.pushButton_6.setGeometry(QtCore.QRect(389, 383, 357, 71))
            self.pushButton_6.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 160, 182, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./Image/KOR/guide_open.png);
                }
                QPushButton:hover {
                    background-color: rgb(20, 180, 202); border-radius: 30px;
                }
                ''')
            self.pushButton_6.setObjectName("pushButton_6")
            self.pushButton_6.clicked.connect(self.guidewindow)

            # Button 8 : Language Setting
            self.pushButton_8 = QtWidgets.QPushButton(Form)
            self.pushButton_8.setGeometry(QtCore.QRect(665, 39, 36, 36))
            self.pushButton_8.setStyleSheet("border-radius : 20;")
            self.pushButton_8.setStyleSheet(
                '''
                QPushButton{image:url(./Image/icon/setting.png); border:0px;}
                QPushButton:hover{image:url(./Image/icon/setting_hover.png); border:0px;}
                ''')
            self.pushButton_8.setObjectName("pushButton_8")
            self.pushButton_8.clicked.connect(self.settingWindow)

            # Button 9 : inbody website
            self.pushButton_9 = QtWidgets.QPushButton(Form)
            self.pushButton_9.setGeometry(QtCore.QRect(21, 36, 164, 43))
            self.pushButton_9.setStyleSheet(
                '''
                QPushButton{image:url(./image/inbody.png); border:0px;}
                QPushButton:hover{image:url(./image/inbody_hover.png); border:0px;}
                ''')

            self.pushButton_9.setObjectName("pushButton_9")
            self.pushButton_9.clicked.connect(self.Go_to_inbody)
            # self.pushButton_9.clicked.connect(ui_load.close)

            # Button 10 : Exit Button
            self.pushButton_10 = QtWidgets.QPushButton(Form)
            self.pushButton_10.setGeometry(QtCore.QRect(711, 39, 36, 36))
            self.pushButton_10.setStyleSheet("border-radius : 20;")
            self.pushButton_10.setStyleSheet(
                '''
                QPushButton{image:url(./image/icon/exit.png); border:0px;}
                QPushButton:hover{image:url(./image/icon/exit_hover.png); border:0px;}
                ''')
            self.pushButton_10.setObjectName("pushButton_10")
            self.pushButton_10.clicked.connect(self.exitwindow)

            # 카메라 모니터링
            self.frame = QtWidgets.QFrame(Form)
            self.frame.setGeometry(QtCore.QRect(768, 21, 577, 433))
            self.frame.setAutoFillBackground(False)
            self.frame.setStyleSheet("background-color : rgba(0, 0, 0, 0%); border-radius: 30px;")
            self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
            self.frame.setObjectName("frame")

            self.label_6 = QtWidgets.QLabel(self.frame)
            self.label_6.setGeometry(QtCore.QRect(0, 0, 577, 433))
            self.label_6.setStyleSheet(
                "background-color : white; border-radius: 30px; background: url(./image/default_1366.jpg)", )
            self.label_6.setObjectName("label_6")
            self.label_6.setPixmap(QtGui.QPixmap("../image/default_1366.jpg"))

            self.cam_frame = QtWidgets.QLabel(self.frame)
            self.cam_frame.setGeometry(QtCore.QRect(0, 0, 577, 433))
            self.cam_frame.setStyleSheet("background-color : rgba(0,0,0,0%);")
            self.cam_frame.setObjectName("cam_frame")
            if DARK_MODE:
                self.cam_frame.setPixmap(QtGui.QPixmap("../image/cam_frame_dark_1366.png"))
            else:
                self.cam_frame.setPixmap(QtGui.QPixmap("../image/cam_frame_1366.png"))


            # self.loading = QtWidgets.QLabel(Form)
            # self.loading.setGeometry(QtCore.QRect(405, 304, 300, 500))
            # self.loading.setStyleSheet("background-color : rgba(0,0,0,0%);")
            # self.loading.setObjectName("loading")

            # self.script_frame = QtWidgets.QLabel(Form)
            # self.script_frame.setGeometry(QtCore.QRect(30, 668, 100, 100))  # 1860, 350))
            # self.script_frame.setStyleSheet("background-color : rgba(0,250,255,50%);")
            # self.script_frame.setObjectName("script_frame")
            # self.script_frame.setPixmap(QtGui.QPixmap("./image/script_frame.png"))

            self.pushButton_7 = QtWidgets.QPushButton(self.frame)
            self.pushButton_7.setGeometry(QtCore.QRect(610, 540, 200, 60))
            self.pushButton_7.setStyleSheet("border-radius : 55; border : 2px;")
            self.pushButton_7.setStyleSheet("background-color : rgba( 255, 255, 255, 0% );, ")
            self.pushButton_7.setStyleSheet(
                '''
                QPushButton{image:url(./image/KOR/capture.png); border:0px; background-color : rgba( 255, 255, 255, 0% );}
                QPushButton:hover{image:url(./image/KOR/capture_hover.png); border:0px;}
                ''')
            self.pushButton_7.setObjectName("pushButton_7")
            self.pushButton_7.clicked.connect(self.screenshot)
            self.pushButton_7.raise_()

            # 모드제어 프레임
            self.frame_mode = QtWidgets.QFrame(Form)
            self.frame_mode.setGeometry(QtCore.QRect(21, 134, 725, 228))
            self.frame_mode.setAutoFillBackground(False)
            self.frame_mode.setStyleSheet("background-color : rgba(0, 0, 0, 0%)")
            self.frame_mode.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self.frame_mode.setFrameShadow(QtWidgets.QFrame.Raised)
            self.frame_mode.setObjectName("frame_mode")

            self.pushButton = QtWidgets.QPushButton(self.frame_mode)
            self.pushButton.setGeometry(QtCore.QRect(0, 0, 174, 228))
            self.pushButton.setStyleSheet("background-color : #FFFFFF;")



            if DARK_MODE:
                self.pushButton.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/1-2.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/1-2.png); border:0px;}
                    QPushButton{
                    background-color: rgb(47, 56, 77); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(113, 128, 147); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    '''
                )
            else:
                self.pushButton.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/1-1.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/1-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(220, 223, 228); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    '''
                )
            self.pushButton.setCheckable(True)
            self.pushButton.setObjectName("pushButton")
            # self.pushButton_image = QtWidgets.QLabel(self.pushButton)
            # self.pushButton_image.setGeometry(QtCore.QRect(80, 120, 70, 70))
            # self.pushButton_image.setStyleSheet("background-color : rgba(0, 0, 0, 0%)")
            # self.pushButton_image.setStyleSheet(
            #     '''
            #     QLabel{image:url(./image/hand/hand1.png); border:0px;}
            #     '''
            # )
            # self.pushButton.setObjectName("pushButton_image")

            self.pushButton_2 = QtWidgets.QPushButton(self.frame_mode)
            self.pushButton_2.setGeometry(QtCore.QRect(184, 0, 174, 228))
            self.pushButton_2.setStyleSheet("background-color : #FFFFFF;")
            if DARK_MODE:
                self.pushButton_2.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/2-2.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/2-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(113, 128, 147); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    ''')
            else:
                self.pushButton_2.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/2-1.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/2-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(220, 223, 228); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    ''')
            self.pushButton_2.setObjectName("pushButton_2")
            self.pushButton_2.setCheckable(True)
            self.pushButton_3 = QtWidgets.QPushButton(self.frame_mode)
            self.pushButton_3.setGeometry(QtCore.QRect(369, 0, 174, 228))
            if DARK_MODE:
                self.pushButton_3.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/3-2.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/3-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(113, 128, 147); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    ''')
            else:
                self.pushButton_3.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/3-1.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/3-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(220, 223, 228); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    ''')
            self.pushButton_3.setCheckable(True)
            self.pushButton_3.setObjectName("pushButton_3")
            self.pushButton_4 = QtWidgets.QPushButton(self.frame_mode)
            self.pushButton_4.setGeometry(QtCore.QRect(553, 0, 174, 228))
            if DARK_MODE:
                self.pushButton_4.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/4-2.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/4-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(113, 128, 147); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    ''')
            else:
                self.pushButton_4.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/KOR/4-1.png); border:0px;}
                    QPushButton:checked{image:url(./image/KOR/4-2.png); border:0px;}
                    QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                    }
                    QPushButton:hover {
                        background-color: rgb(220, 223, 228); border-radius: 30px;
                    }
                    QPushButton:checked {
                        background-color: rgb(0, 217, 104); border-radius: 30px;
                    }
                    ''')
            self.pushButton_4.setCheckable(True)
            self.pushButton_4.setObjectName("pushButton_4")

            # MainWindow.setCentralWidget(self.centralwidget)

            # self.line = QtWidgets.QFrame(Form)
            # self.line.setGeometry(QtCore.QRect(40, 340, 130, 16))
            # self.line.setStyleSheet("color : #C4BCB8;")
            # self.line.setFrameShadow(QtWidgets.QFrame.Plain)
            # self.line.setLineWidth(10)
            # self.line.setFrameShape(QtWidgets.QFrame.HLine)
            # self.line.setObjectName("line")
            # self.line_2 = QtWidgets.QFrame(Form)
            # self.line_2.setGeometry(QtCore.QRect(350, 340, 130, 16))
            # self.line_2.setStyleSheet("color : #C4BCB8;")
            # self.line_2.setFrameShadow(QtWidgets.QFrame.Plain)
            # self.line_2.setLineWidth(10)
            # self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
            # self.line_2.setObjectName("line_2")
            # self.line_3 = QtWidgets.QFrame(Form)
            # self.line_3.setGeometry(QtCore.QRect(250, 220, 20, 100))
            # self.line_3.setStyleSheet("color : #C4BCB8;")
            # self.line_3.setFrameShadow(QtWidgets.QFrame.Plain)
            # self.line_3.setLineWidth(10)
            # self.line_3.setFrameShape(QtWidgets.QFrame.VLine)
            # self.line_3.setObjectName("line_3")
            # self.line_4 = QtWidgets.QFrame(Form)
            # self.line_4.setGeometry(QtCore.QRect(250, 376, 20, 100))
            # self.line_4.setStyleSheet("color : #C4BCB8;")
            # self.line_4.setFrameShadow(QtWidgets.QFrame.Plain)
            # self.line_4.setLineWidth(10)
            # self.line_4.setFrameShape(QtWidgets.QFrame.VLine)
            # self.line_4.setObjectName("line_4")
            # self.label_4 = QtWidgets.QLabel(Form)
            # self.label_4.setGeometry(QtCore.QRect(214, 320, 100, 56))
            # font = QtGui.QFont()
            # font.setFamily("서울남산 장체B")
            # font.setPointSize(28)
            # self.label_4.setFont(font)
            # self.label_4.setLayoutDirection(QtCore.Qt.LayoutDirectionAuto)
            # self.label_4.setStyleSheet("color : #ACCCC4;")
            # self.label_4.setObjectName("label_4")

            self.menubar = QtWidgets.QMenuBar(Form)
            self.menubar.setGeometry(QRect(0, 0, 870, 21))
            self.menubar.setObjectName("menubar")

            self.pushButton.toggled.connect(lambda: self.togglebutton(Form, integer=0))
            self.pushButton_2.toggled.connect(lambda: self.togglebutton(Form, integer=1))
            self.pushButton_3.toggled.connect(lambda: self.togglebutton(Form, integer=2))
            self.pushButton_4.toggled.connect(lambda: self.togglebutton(Form, integer=3))

            self.pushButton_5.toggled.connect(ui_load.open)
            #self.pushButton_4.clicked.connect(self.loading.closeEvent)
            self.pushButton_5.toggled.connect(lambda: self.checked(Form))


            self.thread = Opcv()

            self.click_mode.connect(self.thread.mode_setting)
            self.button6_checked.connect(self.thread.send_img)
            # self.power_off_signal.connect(self.thread.send_img)
            self.thread.change_pixmap_signal.connect(self.update_img)
            self.thread.mode_signal.connect(self.push_button)

            # self.pushButton.setEnabled(False)
            # self.pushButton_2.setEnabled(False)
            # self.pushButton_3.setEnabled(False)
            # self.pushButton_4.setEnabled(False)
            # self.pushButton_7.setEnabled(False)
            # self.button6_checked.emit(False)

            self.thread.start()


            # thread_load
            # self.thread_load = Load()
            ui.setupLanguage(ui, language_setting, DARK_MODE, LEFT)

            self.retranslateUi(Form)
            QtCore.QMetaObject.connectSlotsByName(Form)

        def setupLanguage(self, Form, language, DARK_MODE, left):
            print('setupLanguage')
            global language_setting
            # global DARK_MODE

            if not DARK_MODE: Form.setStyleSheet("background-color : rgb(248, 249, 251);");
            else: Form.setStyleSheet("background-color : rgb(32, 36, 47);");
            if not DARK_MODE: Form.label.setStyleSheet("color : rgb(32, 36, 47);");
            else: Form.label.setStyleSheet("color : rgb(248, 249, 251);");
            if DARK_MODE:
                Form.cam_frame.setPixmap(QtGui.QPixmap("../image/cam_frame_dark_1366.png"))
            else:
                Form.cam_frame.setPixmap(QtGui.QPixmap("../image/cam_frame_1366.png"))
            if DARK_MODE:
                self.pushButton_10.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/icon/exit_dark.png); border:0px;}
                    QPushButton:hover{image:url(./image/icon/exit_dark_hover.png); border:0px;}
                    ''')
                self.pushButton_8.setStyleSheet(
                    '''
                    QPushButton{image:url(./Image/icon/setting_dark.png); border:0px;}
                    QPushButton:hover{image:url(./Image/icon/setting_dark_hover.png); border:0px;}
                    ''')
                self.pushButton_9.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/inbody_dark.png); border:0px;}
                    QPushButton:hover{image:url(./image/inbody_hover.png); border:0px;}

                    ''')
                self.label_6.setPixmap(QtGui.QPixmap("../image/default_dark_1366.jpg"))
            else:
                self.pushButton_10.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/icon/exit.png); border:0px;}
                    QPushButton:hover{image:url(./image/icon/exit_hover.png); border:0px;}
                    ''')
                self.pushButton_8.setStyleSheet(
                    '''
                    QPushButton{image:url(./Image/icon/setting.png); border:0px;}
                    QPushButton:hover{image:url(./Image/icon/setting_hover.png); border:0px;}
                    ''')
                self.pushButton_9.setStyleSheet(
                    '''
                    QPushButton{image:url(./image/inbody.png); border:0px;}
                    QPushButton:hover{image:url(./image/inbody_hover.png); border:0px;}

                    ''')
                self.label_6.setPixmap(QtGui.QPixmap("../image/default_1366.jpg"))
            if language == '한국어(Korean)':
                if not DARK_MODE:
                    self.pushButton.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/1-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/1-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_2.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/2-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/2-2.png); border:0px;}
                                            QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')

                    self.pushButton_3.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/3-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/3-2.png); border:0px;}
                                            QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_4.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/4-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/4-2.png); border:0px;}
                                            QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_7.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/capture.png); border:0px;}
                        QPushButton:hover{image:url(./image/KOR/capture_hover.png); border:0px;}
                        ''')
                    self.pushButton_5.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(226, 0, 46, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./image/KOR/cam_on.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                        }
                        QPushButton:checked{
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                            image:url(./image/KOR/cam_off.png);
                            }
                        ''')
                    self.pushButton_6.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(0, 160, 182, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./Image/KOR/guide_open.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(20, 180, 202); border-radius: 30px;
                        }
                        ''')
                else:
                    self.pushButton.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/1-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/1-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_2.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/2-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/2-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_3.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/3-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/3-2.png); border:0px;}
                                            QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_4.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/4-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/KOR/4-2.png); border:0px;}
                                            QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_7.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/KOR/capture.png); border:0px;}
                        QPushButton:hover{image:url(./image/KOR/capture_hover.png); border:0px;}
                        ''')
                    self.pushButton_5.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(226, 0, 46, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./image/KOR/cam_on.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                        }
                        QPushButton:checked{
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                            image:url(./image/KOR/cam_off.png);
                            }
                        ''')
                    self.pushButton_6.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(0, 160, 182, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./Image/KOR/guide_open.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(20, 180, 202); border-radius: 30px;
                        }
                        ''')
            elif language == '영어(English)':
                if not DARK_MODE:
                    self.pushButton.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/1-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/1-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_2.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/2-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/2-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_3.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/3-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/3-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_4.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/4-1.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/4-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(233, 236, 241); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(220, 223, 228); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_7.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/capture.png); border:0px;}
                        QPushButton:hover{image:url(./image/ENG/capture_hover.png); border:0px;}
                        ''')
                    self.pushButton_5.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(226, 0, 46, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./image/ENG/cam_on.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                        }
                        QPushButton:checked{
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                            image:url(./image/ENG/cam_off.png);
                            }
                        ''')
                    self.pushButton_6.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(0, 160, 182, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./Image/ENG/guide_open.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(20, 180, 202); border-radius: 30px;
                        }
                        ''')
                else:
                    self.pushButton.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/1-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/1-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_2.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/2-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/2-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_3.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/3-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/3-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_4.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/4-2.png); border:0px;}
                        QPushButton:checked{image:url(./image/ENG/4-2.png); border:0px;}
                        QPushButton{
                        background-color: rgb(47, 56, 77); border-radius: 30px;
                        }
                        QPushButton:hover {
                            background-color: rgb(113, 128, 147); border-radius: 30px;
                        }
                        QPushButton:checked {
                            background-color: rgb(0, 217, 104); border-radius: 30px;
                        }
                        ''')
                    self.pushButton_7.setStyleSheet(
                        '''
                        QPushButton{image:url(./image/ENG/capture.png); border:0px;}
                        QPushButton:hover{image:url(./image/ENG/capture_hover.png); border:0px;}
                        ''')
                    self.pushButton_5.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(226, 0, 46, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./image/ENG/cam_on.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                        }
                        QPushButton:checked{
                            background-color: rgb(246, 20, 66); border-radius: 30px;
                            image:url(./image/ENG/cam_off.png);
                            }
                        ''')
                    self.pushButton_6.setStyleSheet(
                        '''
                        QPushButton{
                            color: white;
                            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                            stop:0 rgba(0, 160, 182, 255),
                            stop:1 rgba(144, 61, 167, 255));
                            border-radius: 30px;
                            image:url(./Image/ENG/guide_open.png);
                        }
                        QPushButton:hover {
                            background-color: rgb(20, 180, 202); border-radius: 30px;
                        }
                        ''')

            with open('../setting.json', 'r', encoding='UTF8') as json_file:
                json_data = json.load(json_file)
                new_data = json_data
            new_data['DARK_MODE'] = str(DARK_MODE)
            new_data['LANGUAGE'] = language
            new_data['LEFT'] = left
            print(new_data)
            with open('../setting.json', 'w', encoding='UTF8') as json_file:
                json.dump(new_data, json_file, indent="\t")

        def retranslateUi(self, Form):
            _translate = QtCore.QCoreApplication.translate
            Form.setWindowTitle(_translate("Form", "Motion Presentation V 1.4"))
            # self.label_2.setText(_translate("Form", "Presentation Tool"))
            # self.label_3.setText(_translate("Form", "1.2"))
            # 여기다가
            # self.label.setText(_translate("Form", "Motion Presentation"))
            # self.label_4.setText(_translate("Form", "MODE"))

        def exitDialog(self):
            msgBox = QMessageBox()
            # msgBox.setMinimumSize(QSize(1000, 500))
            msgBox.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)  # | QtCore.Qt.WindowStaysOnTopHint)
            msgBox.setIcon(QMessageBox.Information)
            # msgBox.setStyleSheet("background-color:rgba(255, 255, 255, 255);")
            if not DARK_MODE: msgBox.setStyleSheet("background-color : rgb(248, 249, 251);");
            else: msgBox.setStyleSheet("background-color : rgb(32, 36, 47);");
            # msgBox.resizeEvent(500, 500)
            font = QtGui.QFont()
            font.setFamily("서울남산 장체B")
            font.setPointSize(22)

            msgBox.setFont(font)
            msgBox.setText("프로그램을 종료하시겠습니까?")
            msgBox.setWindowTitle("Exit?")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                system("taskkill /f /im ZoomIt64.exe")
                system("taskkill /f /im ZoomIt.exe")
                sys.exit()

            msgBox.pushButton_ok = QtWidgets.QPushButton(msgBox)
            msgBox.pushButton_ok.setGeometry(QtCore.QRect(30, 271, 261, 100))
            msgBox.pushButton_ok.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 217, 104, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/OK.png);
                }
                QPushButton:hover {
                    background-color: rgb(0, 217, 104); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(0, 217, 104); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            msgBox.pushButton_ok.setObjectName("pushButton_ok")
            msgBox.pushButton_ok.clicked.connect(msgBox.accept)
            msgBox.pushButton_ok.clicked.connect(msgBox.getComboBoxItem)

            msgBox.pushButton_cancel = QtWidgets.QPushButton(msgBox)
            msgBox.pushButton_cancel.setGeometry(QtCore.QRect(310, 271, 261, 100))
            msgBox.pushButton_cancel.setStyleSheet(
                '''
                QPushButton{
                    color: white;
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0.857143, y2:0.857955,
                    stop:0 rgba(0, 160, 182, 255),
                    stop:1 rgba(144, 61, 167, 255));
                    border-radius: 30px;
                    image:url(./image/Cancel.png);
                }
                QPushButton:hover {
                    background-color: rgb(246, 20, 66); border-radius: 30px;
                }
                QPushButton:checked{
                    background-color: rgb(246, 20, 66); border-radius: 30px;
                    image:url(./image/KOR/cam_off.png);
                    }
                ''')
            self.pushButton_cancel.setObjectName("pushButton_cancel")

        @pyqtSlot(int)
        def push_button(self, integer):  # 2-1
            if integer != -1:
                B_list = [self.pushButton, self.pushButton_2,
                          self.pushButton_3, self.pushButton_4]
                if not B_list[integer].isChecked():
                    self.From_button = True
                    B_list[integer].toggle()  # #2-2
            else:
                self.From_button = False
                pass

        def togglebutton(self, Form, integer):
            Button_list = [self.pushButton, self.pushButton_2,
                           self.pushButton_3, self.pushButton_4]
            Before_mode_list = []
            if Button_list[integer].isChecked():  # 2-3
                Button_list.pop(integer)
                for button in Button_list:
                    if button.isChecked():
                        button.toggle()
                        Before_mode_list.append(button)

                if len(Before_mode_list) != 0:
                    if self.From_button == False:
                        if Before_mode_list[0] == self.pushButton:
                            self.click_mode.emit(integer + 1, 1)
                        elif Before_mode_list[0] == self.pushButton_2:
                            self.click_mode.emit(integer + 1, 2)
                        elif Before_mode_list[0] == self.pushButton_3:
                            self.click_mode.emit(integer + 1, 3)
                        elif Before_mode_list[0] == self.pushButton_4:
                            self.click_mode.emit(integer + 1, 4)
                    else:
                        self.click_mode.emit(integer + 1, integer + 1)
                else:
                    if self.From_button == False:
                        self.click_mode.emit(integer + 1, 0)
                    else:
                        self.click_mode.emit(integer + 1, integer + 1)
            else:
                pass

        def screenshot(self):
            # print('clicked')
            now = datetime.datetime.now().strftime("%d_%H-%M-%S")
            filename = './screenshots/' + str(now) + ".jpg"
            print('Saving image as ' + filename)
            image = self.label_6.pixmap()
            # print(image.size())
            image.save(filename)

        def cvt_qt(self, img, size=(577, 433)):
            # rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # cv 이미지 파일 rgb 색계열로 바꿔주기
            h, w, ch = img.shape  # image 쉐입 알기
            bytes_per_line = ch * w  # 차원?
            convert_to_Qt_format = QtGui.QImage(img.data, w, h, bytes_per_line,
                                                QtGui.QImage.Format_RGB888)  # qt 포맷으로 바꾸기
            p = convert_to_Qt_format.scaled(577, 433, QtCore.Qt.KeepAspectRatio)  # 디스클레이 크기로 바꿔주기.

            return QtGui.QPixmap.fromImage(p)  # 진정한 qt 이미지 생성

        @pyqtSlot(np.ndarray)
        def update_img(self, img):
            qt_img = self.cvt_qt(img)
            self.label_6.setPixmap(qt_img)

        def checked(self, Form):
            # self.loading.setGeometry(10, 10, 100, 200)
            # loading_window = Load_window()
            # loading_window.setupUi(loading_window)
            # loading_window.exec_()
            print('loading...')
            # dlg = Loading()
            # dlg.setupUi(dlg)
            # dlg.exec_()
            self.label_6.setStyleSheet(
                "background-color : white; border-radius: 50px;" )
            self.label_6.setObjectName("label_6")
            if DARK_MODE:
                self.label_6.setPixmap(QtGui.QPixmap("../image/default_dark_1366.jpg"))
            else:
                self.label_6.setPixmap(QtGui.QPixmap("../image/default_1366.jpg"))

            if self.pushButton_5.isChecked():
                # image = cv2.imread('./image/testtest.jpg')
                # image = self.cvt_qt(image)
                # self.label_6.setPixmap(image)
                # self.label_6.setPixmap(QtGui.QPixmap("./image/testtest.jpg"))
                # self.label_6.setStyleShee
                # loading_window.reject()
                self.pushButton.setEnabled(True)
                self.pushButton_2.setEnabled(True)
                self.pushButton_3.setEnabled(True)
                self.pushButton_4.setEnabled(True)
                self.pushButton_7.setEnabled(True)

                self.button6_checked.emit(True)

            else:
                self.pushButton.setEnabled(False)
                self.pushButton_2.setEnabled(False)
                self.pushButton_3.setEnabled(False)
                self.pushButton_4.setEnabled(False)
                self.pushButton_7.setEnabled(False)
                self.button6_checked.emit(False)
                Button_list = [self.pushButton, self.pushButton_2,
                               self.pushButton_3, self.pushButton_4]
                for button in Button_list:
                    if button.isChecked():
                        button.toggle()
                self.button6_checked.emit(False)
                print('Default image set')
                #self.label_6.setPixmap(QtGui.QPixmap("./image/default.jpg"))
                if ui_load.status == 1:
                    ui_load.close()
                    ui_load.status = 0

        def settingWindow(self):
            sound = sounds[9]
            sound.play()
            dlg = Setting_window()
            dlg.setupUi(dlg)
            dlg.exec_()

        def guidewindow(self):
            sound = sounds[9]
            sound.play()
            path = os.getcwd()
            guide_path = path + "\\guide\\0\\0.html"
            os.system('''../open_guide.bat''')

        def exitwindow(self):
            sound = sounds[9]
            sound.play()
            dlg = Exit_window()
            dlg.setupUi(dlg)
            dlg.exec_()

        # 대본영역
        def updateMask(self):
            # get the *whole* window geometry, including its titlebar and borders
            frameRect = self.frameGeometry()
            # print(frameRect)
            # get the grabWidget geometry and remap it to global coordinates
            grabGeometry = self.grabWidget.geometry()
            grabGeometry = QtCore.QRect(0, 0, 1323, 249)
            # 30, 668
            grabGeometry.moveTopLeft(self.grabWidget.mapToGlobal(QtCore.QPoint(30, 668)))

            # get the actual margins between the grabWidget and the window margins
            left = frameRect.left() - grabGeometry.left()
            top = frameRect.top() - grabGeometry.top()
            right = frameRect.right() - grabGeometry.right()
            bottom = frameRect.bottom() - grabGeometry.bottom()

            # reset the geometries to get "0-point" rectangles for the mask
            frameRect.moveTopLeft(QtCore.QPoint(21, 475))
            grabGeometry.moveTopLeft(QtCore.QPoint(21, 475))

            # create the base mask region, adjusted to the margins between the
            # grabWidget and the window as computed above
            region = QtGui.QRegion(frameRect.adjusted(left, top, right, bottom))

            # "subtract" the grabWidget rectangle to get a mask that only contains
            # the window titlebar, margins and panel
            region -= QtGui.QRegion(grabGeometry)
            self.setMask(region)

            # update the grab size according to grabWidget geometry
            self.widthLabel.setText(str(self.grabWidget.width()))
            self.heightLabel.setText(str(self.grabWidget.height()))

        def paintEvent(self, event):
            super(Grabber, self).paintEvent(event)
            # on Linux the frameGeometry is actually updated "sometime" after show()
            # is called; on Windows and MacOS it *should* happen as soon as the first
            # non-spontaneous showEvent is called (programmatically called: showEvent
            # is also called whenever a window is restored after it has been
            # minimized); we can assume that all that has already happened as soon as
            # the first paintEvent is called; before then the window is flagged as
            # "dirty", meaning that there's no need to update its mask yet.
            # Once paintEvent has been called the first time, the geometries should
            # have been already updated, we can mark the geometries "clean" and then
            # actually apply the mask.
            if self.dirty:
                # 대본 영역 없앨 것 (1.4.2)
                self.updateMask()
                self.dirty = False

        def Go_to_inbody(self):
            os.system('explorer https://www.inbody.com/kr/')


    ui = Grabber()
    ui.setupUi(ui)
    ui.show()

    # ui.MainWindow.show()
    sys.exit(app.exec_())
    sys.exit(ui.exec_())


if __name__ == '__main__':
    # print("")

    print('Running main_1_4_2.py...')

    # system('ZoomIt.exe')

    system('python main_1_4_2.py')
