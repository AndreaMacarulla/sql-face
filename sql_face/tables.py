# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_tables.ipynb.

# %% auto 0
__all__ = ['Image', 'SCFaceMixin', 'EnfsiMixin', 'VideoMixin', 'EnfsiImage', 'SCImage', 'VideoFrame', 'CPFrame',
           'EnfsiVideoFrame', 'Pair', 'EnfsiPair', 'EnfsiPair2015', 'Detector', 'CroppedImage', 'EmbeddingModel',
           'FaceImage', 'QualityModel', 'QualityImage']

# %% ../nbs/03_tables.ipynb 3
from typing import Tuple

from sqlalchemy import Column, Integer, String, Enum, Boolean, PickleType, ForeignKey, Table, Float
from sqlalchemy.orm import relationship, declarative_mixin, declared_attr
from sqlalchemy.ext.declarative import declarative_base

from deepface import DeepFace
import cv2
import enum
import numpy as np

import os


# %% ../nbs/03_tables.ipynb 4
#To start table creation.
Base = declarative_base()

# %% ../nbs/03_tables.ipynb 6
## All the attribute Enum for the Image.


class Gender(enum.Enum):
    MALE = "Man"
    FEMALE = "Woman"

class Age(enum.Enum):
    # todo: fill enum with age number.
    CHILD = "0-12"
    ADOLESCENT = '13-17'
    YOUNG_ADULT = '18-30'
    ADULT = '31-45'
    MIDDLE_AGED_ADULT = '46-64'
    SENIOR = '65-100'

    @staticmethod
    def age2enum(age:int)->Enum:
        if age > 65:
            age_enum = Age.SENIOR
        elif age > 45:
            age_enum = Age.MIDDLE_AGED_ADULT
        elif age > 30:
            age_enum = Age.ADULT
        elif age > 18:
            age_enum = Age.YOUNG_ADULT
        elif age > 12:
            age_enum = Age.ADOLESCENT
        elif age > 0:
            age_enum = Age.CHILD
        else:
            age_enum = None
            print(f'Age {age} not in range, None returned')

        return age_enum


class Yaw(enum.Enum):
    FRONTAL = "straight"
    HALF_TURNED = "slightly_turned"
    PROFILE = "sideways"


class Pitch(enum.Enum):
    UP = "upwards"
    HALF_UP = "slightly_upwards"
    FRONTAL = "straight"
    HALF_DOWN = "slightly_downwards"
    DOWN = "downwards"
    
class Roll(enum.Enum):
    FRONTAL = "straight"
    HALF_LEANING = "slightly_inclined"
    HORIZONTAL = "completely_inclined"

class Emotion(enum.Enum):
    # TODO: implementChange to expression
    '''angry, fear, neutral, sad, disgust, happy and surprise'''
    ANGRY = 'angry'
    FEAR = 'fear'
    NEUTRAL = 'neutral'
    SAD = 'sad'
    DISGUST = 'disgust'
    HAPPY = 'happy'
    SURPRISE = 'surprise'
    

class Race(enum.Enum):
    '''asian, white, middle eastern, indian, latino and black'''
    ASIAN='asian'
    WHITE = 'white'
    MIDDLE_EASTERN = 'middle eastern'
    INDIAN = 'indian'
    LATINO = 'latino hispanic'
    BLACK = 'black'


class Distance(enum.Enum):
    '''asian, white, middle eastern, indian, latino and black'''
    FRONTAL = 50
    SHORT= 100
    MEDIUM= 260
    FAR = 420

class QualityGroup(enum.Enum):
    VERY_LOW = "Very low"
    LOW = "Low"
    MEDIUM = 'Medium'
    HIGH = 'High'
    VERY_HIGH = 'Very high'

# %% ../nbs/03_tables.ipynb 8
class Image(Base):
    "Image SQL class"
    __tablename__ = "image"
    image_id = Column(Integer, primary_key=True) # Image primary key
    path = Column(String) # Absolute or relative path
    identity = Column(String) # Person identity of the image
    source = Column(String) # Database the image belongs to
    gender = Column(Enum(Gender))
    age = Column(Enum(Age))
    age_number = Column(Float)
    emotion = Column(Enum(Emotion))
    race = Column(Enum(Race))
    yaw = Column(Enum(Yaw))
    pitch = Column(Enum(Pitch))
    roll = Column(Enum(Roll))
    headgear = Column(Boolean)
    glasses = Column(Boolean)
    beard = Column(Boolean)
    other_occlusions = Column(Boolean)
    low_quality = Column(Boolean)
    angle_yaw = Column(Float)
    angle_pitch = Column(Float)
    angle_roll = Column(Float)
    # image_quality = Column(Enum(Quality))
    

    type = Column(String)
    __mapper_args__ = {
        'polymorphic_identity': 'image',
        'polymorphic_on': type
    }

    croppedImages = relationship("CroppedImage", back_populates="images", lazy='subquery')

    def get_image(self, input_dir:str):
        abs_path = os.path.join(input_dir, self.path)
        return cv2.imread(abs_path)

    def get_category(self, im_category_list, fi_cat_list, detector, embedding_model):
        # todo: clean some day.
        return tuple(
            self.get_im_category(im_category_list) )
            # + self.get_fi_category(fi_cat_list, detector, embedding_model))

    def get_im_category(self, im_category_list):
        category_values = [self.__dict__[category] for category in im_category_list]
        return category_values

    def get_fi_category(self, fi_cat_list, detector, embedding_model):
        # todo: if more face image categories are added, change function.
        confusion_score = [face_image.confusion_score for cropped_image in self.croppedImages if
                           cropped_image.detectors.name == detector
                           for face_image in cropped_image.faceImages if
                           face_image.embeddingModels.name == embedding_model]
        assert len(confusion_score) <= 1
        if len(confusion_score) == 0:
            return None
        if not fi_cat_list:
            return []
        return confusion_score  # list as it were several categories.


# %% ../nbs/03_tables.ipynb 10
@declarative_mixin
class SCFaceMixin:
    "SC Face database mixin"
    sc_type = Column(String)
    distance = Column(Enum(Distance))
    infrared = Column(Boolean)

    @declared_attr
    def image_id(cls):
        return Column(Integer, ForeignKey('image.image_id'), primary_key=True)

# %% ../nbs/03_tables.ipynb 11
@declarative_mixin
class EnfsiMixin:
    "ENFSI database mixin"
    year = Column(Integer)

    @declared_attr
    def image_id(cls):
        return Column(Integer, ForeignKey('image.image_id'), primary_key=True)

# %% ../nbs/03_tables.ipynb 12
@declarative_mixin
class VideoMixin:
    source_video = Column(String)
    n_frame = Column(Integer)

    @declared_attr
    def image_id(cls):
        return Column(Integer, ForeignKey('image.image_id'), primary_key=True)

    def get_image(self, input_dir):
        abs_path = os.path.join(input_dir,self.path)
        video = cv2.VideoCapture(abs_path)
        video.set(1, self.n_frame)
        ret, image = video.read()
        if ret:
            return image

# %% ../nbs/03_tables.ipynb 14
class EnfsiImage(EnfsiMixin, Image):
    __tablename__ = 'enfsiImage'
    __mapper_args__ = {
        'polymorphic_identity': 'enfsiImage',
    }

# %% ../nbs/03_tables.ipynb 16
class SCImage(SCFaceMixin, Image):    
    __tablename__ = 'scImage'
    __mapper_args__ = {
        'polymorphic_identity': 'scImage',
    }

# %% ../nbs/03_tables.ipynb 18
class VideoFrame(VideoMixin, Image):
    __tablename__ = 'videoFrame'
    __mapper_args__ = {
        'polymorphic_identity': 'videoFrame',
    }

# %% ../nbs/03_tables.ipynb 19
class CPFrame(VideoFrame):
    # "ChokePoint video frame"
    #__tablename__ = 'cpVideoFrame'
    __mapper_args__ = {
        'polymorphic_identity': 'cpVideoFrame',
    }

    def get_image(self, input_dir):
        """Especial method for getting the images in ChokePoint.
        """
        return Image.get_image(self, input_dir)

# %% ../nbs/03_tables.ipynb 20
class EnfsiVideoFrame(EnfsiMixin, VideoMixin, Image):
    __tablename__ = 'enfsiVideoFrame'
    __mapper_args__ = {
        'polymorphic_identity': 'enfsiVideoFrame',
    }

# %% ../nbs/03_tables.ipynb 22
class Pair:
    def __init__(self, first:Image, second:Image):
        self.first = first
        self.second = second
        self.same_identity = self.is_same()
        self.n_common_attributes = self.get_n_common_attributes()



    def is_same(self):
        """
        Returns whether or not the two images in this pair share the same
        identity or not.

        :return: bool
        """
        return self.first.identity == self.second.identity and self.first.source == self.second.source

    

    def get_n_common_attributes(self):
        n = 0
        attrs = ['gender', 'age', 'emotion', 'race', 'yaw', 'pitch', 'roll', 'headgear', 'glasses', 'beard', 'other_occlusions']
        for attr in attrs:
            if getattr(self.first, attr) is not None and getattr(self.first, attr) == getattr(self.second, attr):
                n += 1
        return n

        

    def get_category(self, im_category_list, fi_cat_list, detector, embedding_model):
        return tuple((self.first.get_category(im_category_list, fi_cat_list, detector, embedding_model),
                      self.second.get_category(im_category_list, fi_cat_list, detector, embedding_model)))

    def is_valid(self, detector: str):
        return self.first.is_valid(detector=detector) and self.second.is_valid(detector=detector)

    def pair_category_str(self, category_list):
        pair_category = ';'.join(self.get_category(self, category_list))
        return f'({pair_category})'

    def make_cropped_pair(self, detector):
        first_cropped_image = self.first.make_cropped_image(detector=detector)
        second_cropped_image = self.second.make_cropped_image(detector=detector)
        return CroppedPair(first_cropped_image, second_cropped_image)

    def make_face_image_pair(self, session, detector, embedding_model):
        if embedding_model == 'FaceVACs':
            facevacs_pair = (session.query(FaceVACsPair)
                             .filter(FaceVACsPair.first_id == self.first_id,
                                     FaceVACsPair.second_id == self.second_id)
                             .one_or_none()
                             )
            return facevacs_pair
        else:
            first_face_image = (session.query(FaceImage)
                                .join(CroppedImage)
                                .join(Detector)
                                .join(EmbeddingModel)
                                .filter(CroppedImage.image_id == self.first.image_id,
                                        CroppedImage.face_detected == True,
                                        Detector.name == detector,
                                        EmbeddingModel.name == embedding_model)
                                .one_or_none()
                                )
            second_face_image = (session.query(FaceImage)
                                 .join(CroppedImage)
                                 .join(Detector)
                                 .join(EmbeddingModel)
                                 .filter(CroppedImage.image_id == self.second.image_id,
                                         CroppedImage.face_detected == True,
                                         Detector.name == detector,
                                         EmbeddingModel.name == embedding_model)
                                 .one_or_none()
                                 )

            return FacePair(first_face_image, second_face_image, self.same_identity)

# %% ../nbs/03_tables.ipynb 23
class EnfsiPair(Base, Pair):

    __tablename__ = "enfsiPair"
    enfsiPair_id = Column(Integer, primary_key=True)
    
    same = Column(Boolean)
    ExpertsLLR = Column(PickleType)

    first_id = Column(Integer, ForeignKey('enfsiImage.image_id'))
    # todo: does it make a difference to fill with images or enfsi images here?
    second_id = Column(Integer, ForeignKey('enfsiImage.image_id'))

    first = relationship("EnfsiImage", foreign_keys=[first_id])
    second = relationship("EnfsiImage", foreign_keys=[second_id])

    enfsi_type = Column(String)
    __mapper_args__ = {
        'polymorphic_identity': 'enfsiPair',
        'polymorphic_on': enfsi_type
    }



# %% ../nbs/03_tables.ipynb 24
class EnfsiPair2015(EnfsiPair):

    __tablename__ = 'enfsiPair2015'
    enfsiPair2015_id = Column(Integer, ForeignKey('enfsiPair.enfsiPair_id'), primary_key=True)

    comparison = Column(Integer)

    # todo: repeated column in enfsipair and enfsipair2015. Should be deleted from enfsipair2015.
    first_id = Column(Integer, ForeignKey('enfsiVideoFrame.image_id'))
    first = relationship("EnfsiVideoFrame", foreign_keys=[first_id])



    __mapper_args__ = {
        'polymorphic_identity': 'enfsiPair2015',
    }

# %% ../nbs/03_tables.ipynb 26
class Detector(Base):
    "Detector SQL class"
    __tablename__ = "detector"
    detector_id = Column(Integer, primary_key=True)
    name = Column(String)

# %% ../nbs/03_tables.ipynb 27
class CroppedImage(Base):
    __tablename__ = 'croppedImage'
    croppedImage_id = Column(Integer, primary_key=True)

    image_id = Column(Integer, ForeignKey('image.image_id'))
    detector_id = Column(Integer, ForeignKey('detector.detector_id'))

    bounding_box = Column(PickleType)
    landmarks = Column(PickleType)
    face_detected = Column(Boolean)

    images = relationship("Image", foreign_keys=[image_id])
    detectors = relationship("Detector", foreign_keys=[detector_id])
    faceImages = relationship("FaceImage", back_populates="croppedImages")

    def get_cropped_image(self, input_dir):
        image = self.images.get_image(input_dir)
        if self.face_detected:
            return image[self.bounding_box[1]:self.bounding_box[1] + self.bounding_box[3],
                   self.bounding_box[0]:self.bounding_box[0] + self.bounding_box[2], :]
        else:
            return image

    def get_aligned_image(self, input_dir, target_size:Tuple[int,int]=(112,112), ser_fiq = None):
        image = self.images.get_image(input_dir)        
        
        if self.detectors.name == 'mtcnn_serfiq':
             
            aligned_image = ser_fiq.apply_mtcnn(image)
            if aligned_image is None:
                print(f'Problems with {self.image_id}, image detected {self.face_detected}')
                return None
            else:
                return np.transpose(aligned_image, (1,2,0))
                
        
        else:
            
            aligned_image = DeepFace.detectFace(img_path = image, 
                                            target_size = target_size, 
                                            detector_backend = self.detectors.name, 
                                            align=True,
                                            enforce_detection=True)
            return aligned_image*255
        
            

# %% ../nbs/03_tables.ipynb 28
class EmbeddingModel(Base):
    __tablename__ = "embeddingModel"
    embeddingModel_id = Column(Integer, primary_key=True)
    name = Column(String)

# %% ../nbs/03_tables.ipynb 29
class FaceImage(Base):
    __tablename__ = 'faceImage'
    faceImage_id = Column(Integer, primary_key=True)

    croppedImage_id = Column(Integer, ForeignKey('croppedImage.croppedImage_id'))
    embeddingModel_id = Column(Integer, ForeignKey('embeddingModel.embeddingModel_id'))

    embeddings = Column(PickleType)
    confusion_score = Column(Float)

    croppedImages = relationship("CroppedImage", foreign_keys=[croppedImage_id])
    embeddingModels = relationship("EmbeddingModel", foreign_keys=[embeddingModel_id])

# %% ../nbs/03_tables.ipynb 30
class QualityModel(Base):
    __tablename__ = "qualityModel"
    qualityModel_id = Column(Integer, primary_key=True)
    name = Column(String)
    threshold = Column(PickleType)

# %% ../nbs/03_tables.ipynb 31
class QualityImage(Base):
    __tablename__ = 'qualityImage'
    qualityImage_id = Column(Integer, primary_key=True)

    faceImage_id = Column(Integer, ForeignKey('faceImage.faceImage_id'))
    qualityModel_id = Column(Integer, ForeignKey('qualityModel.qualityModel_id'))

    quality = Column(Float)
    quality_group = Column(Enum(QualityGroup))
    quality_vec = Column(PickleType)

    faceImages = relationship("FaceImage", foreign_keys=[faceImage_id])
    qualityModels = relationship("QualityModel", foreign_keys=[qualityModel_id])
