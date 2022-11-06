# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04_databases.ipynb.

# %% auto 0
__all__ = ['DATABASES', 'FaceDataBase', 'LFW', 'get_image_db']

# %% ../nbs/04_databases.ipynb 3
import os 

from abc import ABC, abstractmethod
from typing import List
from tqdm import tqdm

from deepface import DeepFace
from sql_face.tables import *
from sql_face.tables import Gender, Age, Emotion, Race

# %% ../nbs/04_databases.ipynb 4
class FaceDataBase(ABC):
    def __init__(self, 
    input_dir:str,
    source:str
    ):
        self.input_dir= input_dir
        self.source = source
        self.path = self.get_path()
        self.all_image_paths = self.get_all_image_paths()

    
    @abstractmethod
    def get_path(self):
        pass

    
    @abstractmethod
    def get_all_image_paths(self):
        pass


    def paths_not_in_db(self, session):
        db_paths = (
            session.query(Image.path)
            .filter(Image.source == self.source)
            .all()
        )
        db_paths = [row.path for row in db_paths]

        # paths that are not yet in db.
        new_paths = set(self.all_image_paths) - set(db_paths)
        return new_paths

    @staticmethod
    @abstractmethod
    def identity_from_path(paths: List[str]) -> List[str]:
        pass


    def create_images(self, session):
        paths = self.paths_not_in_db(session)
        identities = self.identity_from_path(paths)
        for path, identity in tqdm(zip(paths, identities), desc=f'Creating image record from {self.source}'):
            image = Image(path=path, identity=identity, source=self.source)
            session.add(image)
        session.commit()


    def update_images(self, session, attributes: List[str], force_update: bool = False):

        if 'gender' in attributes:
            self.update_gender(session, force_update)

        if 'age' in attributes:
            self.update_age(session, force_update)

        if 'yaw' in attributes:
            self.update_yaw_roll_pitch(session, force_update)

        if 'emotion' in attributes:
            self.update_emotion(session, force_update)
        
        if 'race' in attributes:
            self.update_race(session, force_update)
        
        if 'distance' in attributes:
            self.update_distance(session, force_update)

    def update_gender(self, session, force_update: bool = False):
        query = session.query(Image).filter(Image.source == self.source)
        if not force_update:
            query = query.filter(Image.gender == None)
        all_img = (query.all())
        for img in tqdm(all_img, desc='Update gender'):
            filters = DeepFace.analyze(img_path=img.get_image(), actions=[
                                       'gender'], enforce_detection=False)
            img.gender = Gender(filters["gender"])
            session.commit()

    def update_age(self, session, force_update: bool = False):
        query = session.query(Image).filter(Image.source == self.source)
        if not force_update:
            query = query.filter(Image.age == None)
        all_img = (query.all())
        for img in tqdm(all_img, desc='Update age'):
            filters = DeepFace.analyze(img_path=img.get_image(), actions=[
                                       'age'], enforce_detection=False)
            age = filters["age"]
            img.age_number = age
            img.age = Age.age2enum(age)
            
            
            session.commit()

    

    def update_emotion(self, session, force_update: bool = False):
        query = session.query(Image).filter(Image.source == self.source)
        if not force_update:
            query = query.filter(Image.emotion == None)
        all_img = (query.all())
        for img in tqdm(all_img, desc='Update facial expression (emotion)'):
            filters = DeepFace.analyze(img_path=img.get_image(), actions=[
                                       'emotion'], enforce_detection=False)

            emotions = filters["emotion"]
            prime_emotion = max(emotions, key=emotions.get)
            img.emotion = Emotion(prime_emotion)
            session.commit()

    def update_race(self, session, force_update: bool = False):
        query = session.query(Image).filter(Image.source == self.source)
        if not force_update:
            query = query.filter(Image.race == None)
        all_img = (query.all())
        for img in tqdm(all_img, desc='Update race'):
            filters = DeepFace.analyze(img_path=img.get_image(), actions=[
                                       'race'], enforce_detection=False)

            races = filters["race"]
            prime_race = max(races, key=races.get)
            img.race = Race(prime_race)
            session.commit()


# %% ../nbs/04_databases.ipynb 5
class LFW(FaceDataBase):
    def __init__(self, input_dir):
        super().__init__(input_dir, source = 'LFW')

    def get_path(self)->str:
        return os.path.join(self.input_dir, 'lfw')

    def get_all_image_paths(self)->List[str]:
        paths = []
        for person in os.listdir(self.path):
            if os.path.isdir(os.path.join(self.path, person)):
                person_dir = os.path.join(self.path, person)
                for image_file in os.listdir(person_dir):
                    image_path = os.path.join(person_dir, image_file)
                    paths.append(image_path)
        return paths

    @staticmethod
    def identity_from_path(paths: List[str]) -> List[str]:
        identities = [path.split(os.sep)[-2] for path in paths]
        return identities

    

# %% ../nbs/04_databases.ipynb 6
DATABASES = {'lfw': LFW 
                    # 'xqlfw': XQLFW, 
                    #  'scface': SCFace, 
                    #  'forenface': ForenFace, 
                    #  'utkface': UTKFace,
                    #  'enfsi': Enfsi, 
                    #  'enfsi2015': Enfsi2015
                     }



# %% ../nbs/04_databases.ipynb 7
def get_image_db(input_dir:str,
                database_names:List[str]) -> List[FaceDataBase]:
        """
        Function that converts str names to FaceDataBase class.
        """
        
        all_databases = list(DATABASES.keys())
        for name in database_names:
                if name not in all_databases:
                        raise ValueError(f'Database {name} not contained in the database list. \n \
                        Database list is {all_databases}')
        return [DATABASES[db](input_dir = input_dir) for db in database_names]

# test_fail(lambda: get_image_db('input_dir', ['not_a_db_name']), contains="database name not in the list")
