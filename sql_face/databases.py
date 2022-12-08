# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04_databases.ipynb.

# %% auto 0
__all__ = ['DATABASES', 'FaceDataBase', 'LFW', 'XQLFW', 'UTKFace', 'SCFace', 'Enfsi', 'Enfsi2015', 'ChokePoint', 'get_image_db']

# %% ../nbs/04_databases.ipynb 3
import os
import csv
import cv2
import json
import pandas as pd

from abc import ABC, abstractmethod
from typing import List, Tuple
from tqdm import tqdm

#Read XML
from xml.dom.minidom import parse
import xml.etree.ElementTree as ET

from deepface import DeepFace
from sqlalchemy import or_
from itertools import product

from sql_face.tables import *
from sql_face.tables import Gender, Age, Emotion, Race, Distance, Yaw, Pitch, Roll


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


    def paths_in_db(self, session):        
        db_paths = (
            session.query(Image.path)
            .filter(Image.source == self.source)
            .all()
        )
        db_paths = [row.path for row in db_paths]
        return db_paths

    
    def paths_not_in_db(self, session):
        
        """ 
        db_paths = (
            session.query(Image.path)
            .filter(Image.source == self.source)
            .all()
        )
        db_paths = [row.path for row in db_paths] 
        """

        # paths that are not yet in db.
        new_paths = set(self.all_image_paths) - set(self.paths_in_db(session))
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
    
    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__) and str(self) == str(other)

    def __str__(self) -> str:
        return self.__class__.__name__

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
                    #Change to relative path
                    #image_path = os.path.join(person_dir, image_file)
                    image_path = os.path.join('lfw',person,image_file)
                    paths.append(image_path)
        return paths

    @staticmethod
    def identity_from_path(paths: List[str]) -> List[str]:
        identities = [path.split(os.sep)[-2] for path in paths]
        return identities   

# %% ../nbs/04_databases.ipynb 6
class XQLFW(FaceDataBase):
    def __init__(self, input_dir):
        super().__init__(input_dir, source = 'XQLFW')    
    
    def get_path(self)->str:
        return os.path.join(self.input_dir, 'xqlfw')


    def get_all_image_paths(self) -> List[str]:
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

# %% ../nbs/04_databases.ipynb 7
class UTKFace(FaceDataBase):
    def __init__(self, input_dir):
        super().__init__(input_dir, source = 'UTKface') 
        
        
    def get_path(self)->str:
        return os.path.join(self.input_dir, 'UTKface')


    def get_all_image_paths(self) -> List[str]:
        paths = []
        for image_file in os.listdir(self.path):
            #Change to relative paths
            #image_path = os.path.join(self.path, image_file)
            image_path = os.path.join('UTKface', image_file)
            paths.append(image_path)
        return paths



    def create_images(self, session):
        paths = self.paths_not_in_db(session)
        identities = self.identity_from_path(paths)
        for path, identity in zip(paths, identities):
            image = Image(path=path, identity=identity,
                            source=self.source)
            self.set_age_gender_race(image)
            session.add(image)
        session.commit()

        

    @staticmethod
    def identity_from_path(paths: List[str]) -> List[str]:
        identities = []
        for path in paths:
            base = os.path.split(path)[1]
            filename = os.path.splitext(base)[0]
            identity = filename.split('_')[-1]
            identities.append(identity)

        return identities            

    @staticmethod
    def set_age_gender_race(image:Image):
        base = os.path.split(image.path)[1]
        filename = os.path.splitext(base)[0]
        labels =filename.split('_')[:-1]


        if (len(labels) == 3)  and ('' not in labels):
        
            image.age = Age.age2enum(int(labels[0]))
            image.age_number = float(labels[0])
            if labels[1] == '0':
                gender = Gender('Man')
            elif labels[1] == '1':
                gender = Gender('Woman')
            else:
                raise ValueError(f'Label in file {image.path} is not correct')

            image.gender = gender

            if labels[2] == '0':
                race = Race('white')
            elif labels[2] == '1':
                race = Race('black')

            elif labels[2] == '2':
                race = Race('asian')
        
            elif labels[2] == '3':
                race = Race('indian')
            elif labels[2] == '4':
                race = None

            else:
                raise ValueError(f'Label in file {image.path} is not correct')

            image.race = race     

# %% ../nbs/04_databases.ipynb 8
class SCFace(FaceDataBase):
    def __init__(self, input_dir, types:List[str] =  ["frontal", "rotated", "surveillance"]):
        self.types = types
        self.folders = self._types_to_folders(self.types)        
        super().__init__(input_dir, source = 'SCFace')


    def get_path(self)->str:
        return os.path.join(self.input_dir, 'SCface')

    
    def get_all_image_paths(self) -> List[str]:
        paths = []
        for folder in self.folders:
            abs_folder = os.path.join(self.path, folder)
            for image_file in os.listdir(abs_folder):
                if image_file == 'meta.txt':
                    continue
                image_path = os.path.join(abs_folder, image_file)
                paths.append(image_path)
        return paths

    def create_images(self, session):
        paths = self.paths_not_in_db(session)
        identities = self.identity_from_path(paths)
        types = self.type_from_path(paths)
        for path, identity, type_ in tqdm(zip(paths, identities, types),desc =f'Creating images in {self.source}' ):
            image = SCImage(path=path, identity=identity,
                            source=self.source, sc_type=type_)
            self.set_yaw_pitch_dist(image)
            session.add(image)
        self.set_glasses_beard_gender(session)
        session.commit()
        
    @staticmethod
    def identity_from_path(paths: List[str]) -> List[str]:
        return [os.path.split(path)[1][0:3] for path in paths]

    @staticmethod
    def _types_to_folders(types: List[str]) -> List[str]:
        folders = []
        sc_folders = {"frontal": "mugshot_frontal_cropped_all",
                      "rotated": "mugshot_rotation_all",
                      "surveillance": "surveillance_cameras_all"
                      }
        for type in types:
            if type in sc_folders.keys():
                folders.append(sc_folders[type])
            else:
                raise ValueError(
                    f'Imagetype string value {type} is incorrect, should be one of frontal, rotated or surveillance')
        return folders    

    

    def type_from_path(self, paths: List[str]) -> List[str]:
        path_types = []
        for path in paths:
            current_folder = path.split(os.sep)[-2]
            path_type = [type for type, folder in zip(
                self.types, self.folders) if folder == current_folder]
            assert len(path_type) == 1
            path_types.append(path_type[0])
        return path_types

    @staticmethod
    def set_yaw_pitch_dist(image: SCImage):
        if image.sc_type == 'frontal':
            image.yaw = Yaw.FRONTAL
            image.pitch = Pitch.FRONTAL
            image.low_quality = False
            image.infrared = False
            image.distance = Distance.FRONTAL
        elif image.sc_type == 'rotated':
            image.infrared = False
            image.distance = Distance.FRONTAL
            image.pitch = Pitch.FRONTAL
            image.low_quality = False
            filename = os.path.split(image.path)[-1]
            name, file_extension = os.path.splitext(filename)
            if name[4:] == 'frontal':
                image.yaw = Yaw.FRONTAL
            else:
                yaw_code = int(name[5:])
                if yaw_code == 1:
                    image.yaw = Yaw.HALF_TURNED
                elif yaw_code in (3, 4):
                    image.yaw = Yaw.PROFILE
                elif yaw_code == 2:
                    # code 2 is inconsistent between turned and profile, so we ignore those
                    pass
                else:
                    raise ValueError("Code cannot be mapped")

        elif image.sc_type == 'surveillance':
            dict_distances = {'1': 420, '2': 260, '3': 100}
            image.low_quality = True
            filename = os.path.split(image.path)[-1]
            name, file_extension = os.path.splitext(filename)
            splitted_name = name.split('_')
            if len(splitted_name) == 2:
                image.infrared = True
                image.distance = Distance.FRONTAL
            elif len(splitted_name) == 3:
                image.infrared = False
                image.distance = Distance(dict_distances[splitted_name[-1]])
                if splitted_name[1] > 'cam5':
                    image.infrared = True

            else:
                raise ValueError(f'Name {name} not valid.')
        else:
            raise ValueError(f" {image.sc_type} is not a valid type")


    def set_glasses_beard_gender(self, session):
        with open(os.path.join(self.path, 'SC_face_features.csv')) as f:
            reader = csv.DictReader(f)
            for line in reader:
                idx = line['IDs'].zfill(3)
                gender = Gender('Man')
                if line['G'] == '1':
                    gender = Gender('Woman')
                beard = bool(int(line['B']))
                glasses = bool(int(line['Gl']))
                sc_images = session.query(SCImage).filter(SCImage.identity == idx,
                                                          or_(SCImage.gender == None,
                                                              SCImage.beard == None,
                                                              SCImage.glasses == None,
                                                              SCImage.headgear == None)
                                                          ).all()
                for image in sc_images:
                    image.race = Race('white')
                    image.gender = gender
                    image.beard = beard
                    image.glasses = glasses
                    image.headgear = False
                session.commit()

# %% ../nbs/04_databases.ipynb 9
class Enfsi(FaceDataBase):
    def __init__(self, input_dir, years:List[int]=[2011, 2012, 2013, 2017, 2018, 2019, 2020]):
        self.years = years        
        super().__init__(input_dir, source = 'ENFSI')

    def get_path(self):
        return os.path.join(self.input_dir, 'enfsi')
        
    def get_all_image_paths(self):
        pass

    def identity_from_path(paths: List[str]) -> List[str]:
        pass

    def create_images(self, session):
        for year in self.years:
            folder = os.path.join(self.path, str(year))
            rel_path = os.path.join('enfsi',str(year))
            experts_path = os.path.join(folder, "Experts_LLR.csv")

            with open(os.path.join(folder, 'truth.csv')) as f, open(os.path.join(experts_path)) as exprt:
                reader_experts = pd.read_csv(exprt)
                reader = csv.DictReader(f)

                for line in reader:
                    idx = int(line['id'])
                    same = line['same'] == '1'
                    query, reference = self.get_query_reference(idx, year)

                    reference_id = f'{year}-{idx}'

                    if same:
                        query_id = reference_id
                    else:
                        query_id = f'{reference_id}-unknown'

                    #change folder by rel_path
                    qry_image = self.fill_qry_ref(
                        session, rel_path, query, query_id, year)
                    ref_image = self.fill_qry_ref(
                        session, rel_path, reference, reference_id, year)

                    exp_line = reader_experts.loc[reader_experts['id'] == idx].to_numpy(
                        dtype='float16')
                    experts = exp_line[0, 1:]

                    self.fill_enfsipair(session, qry_image, ref_image, same, experts)
                    session.commit()

    @staticmethod
    def get_query_reference(idx: int, year: int):
        if year < 2013:
            pad_length = 3 if year == 2011 else 2
            query = f'{str(idx).zfill(pad_length)}questioned.jpg'
            reference = f'{str(idx).zfill(pad_length)}reference.jpg'
        elif year == 2018 or year == 2020:
            query = f'{str(idx)}.jpg'
            reference = f'{str(idx)}_BIS.jpg'
        elif year == 2019:
            query = f'2019_{str(idx)}A.jpg'
            reference = f'2019_{str(idx)}B.jpg'
        else:
            query = f'q{str(idx).zfill(2)}.jpg'
            reference = f'r{str(idx).zfill(2)}.jpg'

        return query, reference

    def fill_qry_ref(self, session, folder, path, id, year):
        # folder is relative
        image_path = os.path.join(folder, path)
        image = (
            session.query(EnfsiImage)
            .filter(EnfsiImage.path == image_path)
            .one_or_none()
        )

        if image is None:
            annotation_path = os.path.join(input_dir,
                folder, os.path.splitext(path)[0] + ".json")
            with open(os.path.join(annotation_path)) as ann:
                annotation = json.load(ann)
            image = EnfsiImage(
                path=image_path,
                identity=id,
                source="ENFSI",
                year=year,
                yaw=Yaw(annotation["yaw"]),
                pitch=Pitch(annotation["pitch"]),
                headgear=annotation["headgear"],
                glasses=annotation["glasses"],
                beard=annotation["beard"],
                other_occlusions=annotation["other_occlusions"],
                low_quality=annotation["low_quality"]
            )
            session.add(image)
            session.commit()
        return image


    def fill_enfsipair(self, session, qry_image, ref_image, same, experts):

        enfsi_pair = (
            session.query(EnfsiPair)
            .filter(EnfsiPair.first == qry_image,
                    EnfsiPair.second == ref_image)
            .one_or_none()
        )

        if enfsi_pair is None:
            enfsi_pair = EnfsiPair(
                first=qry_image,
                second=ref_image,
                same=same,
                ExpertsLLR=experts)
            session.add(enfsi_pair)

        session.commit()

# %% ../nbs/04_databases.ipynb 10
class Enfsi2015(FaceDataBase):
    def __init__(self, input_dir):
        super().__init__(input_dir, source = 'ENFSI') 

    def get_path(self):
        return os.path.join(self.input_dir, 'enfsi', '2015')

    def get_all_image_paths(self):
        pass

    def identity_from_path(paths: List[str]) -> List[str]:
        pass

    def create_images(self, session):
        rel_path = os.path.join('enfsi','2015')
        folder = os.path.join(self.path)
        # todo: current experts file is wrong. Change it for the proper one or remove the option.
        # experts_path = os.path.join(folder, "Experts_LLR.csv")

        with open(os.path.join(folder, 'truth.csv')) as f:
            #    , open(os.path.join(experts_path)) as exprt:
            # reader_experts = pd.read_csv(exprt)
            reader = csv.DictReader(f)

            for line in reader:
                idx = int(line['id'])
                same = line['same'] == '1'
                
                #subfolder = os.path.join(self.path, f'Comparison {idx}')
                subfolder = os.path.join(rel_path, f'Comparison {idx}')
                query, references = self.get_query_reference(self.input_dir, subfolder, idx)

                reference_id = f'2015-{idx}'

                if same:
                    query_id = reference_id
                else:
                    query_id = f'{reference_id}-unknown'

                qry_images = self.fill_query(session, self.input_dir, query, query_id)
                ref_images = self.fill_reference(
                    session, references, reference_id)

                # exp_line = reader_experts.loc[reader_experts['id'] == idx].to_numpy(dtype='float16')
                # experts = exp_line[0, 1:]

                self.fill_enfsipair2015(session, qry_images, ref_images, same)
                session.commit()

    @staticmethod
    def get_query_reference(input_dir, subfolder: str, idx: int) -> Tuple[str, List[str]]:
        query = os.path.join(subfolder, 'Questioned', f'CCTV_{idx}.avi')
        # query = f'CCTV_{idx}.avi'
        all_ref_files = os.listdir(os.path.join(input_dir, subfolder, 'Reference'))
        references = [os.path.join(subfolder, 'Reference', fname)
                      for fname in all_ref_files if fname.endswith('.jpg')]
        return query, references

    @staticmethod
    def fill_query(session, input_dir, path, id):
        # todo: what happens if all frames are not saved in the DB (i.e. frames missing?)
        image_path = path
        images = (
            session.query(EnfsiVideoFrame)
            .filter(EnfsiVideoFrame.path == image_path)
            .all()
        )

        if len(images) == 0:
            images = []
            video = cv2.VideoCapture(os.path.join(input_dir, image_path))
            n_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            for n_frame in range(n_frames):
                image = EnfsiVideoFrame(
                    path=image_path,
                    identity=id,
                    source="ENFSI",
                    year=2015,
                    source_video=os.path.basename(image_path),
                    n_frame=n_frame
                )
                session.add(image)
                images.append(image)
            session.commit()

        return images

    @staticmethod
    def fill_reference(session, paths, id):
        images = []
        for path in paths:
            image_path = path
            image = (
                session.query(EnfsiImage)
                .filter(EnfsiImage.path == image_path)
                .one_or_none()
            )

            if image is None:
                image = EnfsiImage(
                    path=image_path,
                    identity=id,
                    source="ENFSI",
                    year=2015,
                )
                session.add(image)
                session.commit()
            images.append(image)

        return images

    @staticmethod
    def fill_enfsipair2015(session, qry_images, ref_images, same):

        for qry_image, ref_image in product(qry_images, ref_images):

            enfsi_pair = (
                session.query(EnfsiPair2015)
                .filter(EnfsiPair2015.first == qry_image,
                        EnfsiPair2015.second == ref_image)
                .one_or_none()
            )

            if enfsi_pair is None:
                enfsi_pair = EnfsiPair2015(
                    first=qry_image,
                    second=ref_image,
                    same=same,
                    comparison=int(ref_image.identity.split('-')[-1])
                )
            session.add(enfsi_pair)

        session.commit()

# %% ../nbs/04_databases.ipynb 11
class ChokePoint(FaceDataBase):
    def __init__(self, input_dir):
        super().__init__(input_dir, source = 'ChokePoint') 

    def get_path(self):
        return os.path.join(self.input_dir, 'ChokePoint')

    def get_all_image_paths(self):
        groundtruth = self.get_groundtruth()
        aip = [os.path.join(self.source,row.videofile,row.frame + '.jpg')
        for index, row in groundtruth.iterrows()]

        return aip
        

    def identity_from_path(paths: List[str]) -> List[str]:    
        pass

    def get_groundtruth(self):
        gfolder = os.path.join(self.get_path(),'groundtruth') # groundtruth folder

        df0 = pd.DataFrame()
        for gfile in os.listdir(gfolder):
            xmlfile = os.path.join(gfolder, gfile)  
            # remove the extension of XML file. Its name contains more than 1 dot
            subfolder = '.'.join(gfile.split('.')[:-1])
            if os.path.isfile(xmlfile):
                frames = []
                persons = []
                # Available in  
                #left_eyes = []
                #right_eyes = []

                tree = ET.parse(xmlfile)
                root = tree.getroot()

                for frame in root:
                    for person in frame:
                        frames.append(frame.attrib['number'])
                        persons.append(person.attrib['id'])


                df = pd.DataFrame(list(zip(frames,persons)) , columns = ['frame','person'])                           
                df['videofile'] = subfolder

                #Remove frames with more than 1 identity
                df = df.drop_duplicates(subset = 'frame', keep = False)

                if len(df0):
                    df0 = df0.append(df,ignore_index = True)
                else:
                    df0 = df.copy()
        return df0
          
        
    
    def create_images(self, session):

        groundtruth = self.get_groundtruth()
        groundtruth['image_path'] = groundtruth.apply(lambda x:
        os.path.join(self.path,x.videofile,x.frame + '.jpg'), axis = 1)

        paths = self.paths_in_db(session)   
        #identities = self.identity_from_path(paths)

        new_images = groundtruth.drop(groundtruth.index[groundtruth['image_path'].isin(paths)]).copy()
        new_images.reset_index(drop = True)
        
        # commit every 300 and at the end
        j = 300
        for index, row in new_images.iterrows():
            #image_path=os.path.join(self.path,row.videofile,row.frame + '.jpg')

            CPimage = CPFrame(
                    path=row.image_path,
                    identity=row.person,
                    source=self.source,
                    
                    source_video=os.path.dirname(row.image_path),
                    n_frame=int(row.frame)
                )
            
            session.add(CPimage)
            j -=1  
            if not j:
                j = 300
                session.commit()

        session.commit()

# %% ../nbs/04_databases.ipynb 12
DATABASES = {'lfw': LFW,
            'xqlfw': XQLFW,
            'utkface': UTKFace,
            'scface': SCFace,
            'enfsi': Enfsi,
            'enfsi2015': Enfsi2015,
            'chokepoint': ChokePoint
            #'forenface': ForenFace,              
                     }

# %% ../nbs/04_databases.ipynb 13
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
