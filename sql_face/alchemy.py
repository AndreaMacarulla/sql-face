# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_alchemy.ipynb.

# %% auto 0
__all__ = ['get_session', 'create_detectors', 'create_embedding_models', 'create_quality_models', 'fill_cropped_image_serfiq',
           'fill_cropped_image_general', 'create_cropped_images', 'create_face_images', 'create_quality_images',
           'update_gender', 'update_age', 'update_emotion', 'update_race', 'update_images', 'update_cropped_images',
           'update_face_images', 'update_embeddings', 'update_quality_images', 'update_ser_fiq', 'update_tface']

# %% ../nbs/02_alchemy.ipynb 3
import os

from typing import List
from tqdm import tqdm

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from deepface.commons import functions
from deepface import DeepFace

from sql_face.databases import FaceDataBase
from sql_face.tables import Base, Image, Detector, CroppedImage, EmbeddingModel, FaceImage, QualityModel, QualityImage 
from sql_face.tables import Gender, Age, Race, Emotion
from sql_face.tface import get_network, compute_tf_quality

# %% ../nbs/02_alchemy.ipynb 5
def get_session(
    output_dir:str, # Output directory
    db_name:str, # .db file name
                    ):  
    db_path = os.path.join(output_dir,db_name+'.db')       
    engine = create_engine(f"sqlite:///{db_path}")
    if not os.path.exists(db_path):
        if not os.path.exists(output_dir):
            print(f'Creating output directory at {output_dir}')
            os.mkdir(output_dir)
            
        print(f'Creating Db file at {db_path}')
        Base.metadata.create_all(engine)

    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session

# %% ../nbs/02_alchemy.ipynb 7
def create_detectors(
                session,
                detector_names: List[str]
                ):
        
        for detector_entry in detector_names:
                detector = (
                        session.query(Detector)
                        .filter(Detector.name == detector_entry)
                        .one_or_none()
                        )
                if detector is None:
                        detector = Detector(name=detector_entry)
                        session.add(detector)
                session.commit()

# %% ../nbs/02_alchemy.ipynb 8
def create_embedding_models(session,
                            embedding_model_names: List[str]):
        
        for emb_model_entry in embedding_model_names:
            emb_model = (
                session.query(EmbeddingModel)
                    .filter(EmbeddingModel.name == emb_model_entry)
                    .one_or_none()
            )
            if emb_model is None:
                emb_model = EmbeddingModel(name=emb_model_entry)
                session.add(emb_model)
        session.commit()


# %% ../nbs/02_alchemy.ipynb 9
def create_quality_models(session,
                            quality_model_names: List[str]):
        
        for qua_model_entry in quality_model_names:
            qua_model = (
                session.query(QualityModel)
                    .filter(QualityModel.name == qua_model_entry)
                    .one_or_none()
            )
            if qua_model is None:
                qua_model = QualityModel(name=qua_model_entry)
                session.add(qua_model)
        session.commit()

# %% ../nbs/02_alchemy.ipynb 10
def fill_cropped_image_serfiq(cr_img: CroppedImage, ser_fiq):
        image = cr_img.images.get_image()
        aligned_img = ser_fiq.apply_mtcnn(image)
        if aligned_img is None:
            cr_img.bounding_box = []
            cr_img.face_detected = False
        elif len(aligned_img) ==0:
            cr_img.bounding_box = []
            cr_img.face_detected = True
        else:
            bbox, points = ser_fiq.detector.detect_face(image)
            cr_img.bounding_box = bbox[0].tolist()
            cr_img.landmarks = points[0].tolist()
            cr_img.face_detected = True

# %% ../nbs/02_alchemy.ipynb 11
def fill_cropped_image_general(cr_img: CroppedImage, **kwargs):
    image = cr_img.images.get_image()      
    
        
    # todo : maybe save the image cropped somewhere?
    try:
        img_cropped, bounding_box = functions.preprocess_face(img=image,
                                                                detector_backend=cr_img.detectors.name,
                                                                enforce_detection=True,
                                                                return_region=True)
        
        cr_img.bounding_box = bounding_box
        cr_img.face_detected = True

    except ValueError:
        cr_img.bounding_box = []
        cr_img.face_detected = False
        # todo: change warning if the image is a video(frame).
        print(f'Face not found in {cr_img.images.path} with {cr_img.detectors.name}')



# %% ../nbs/02_alchemy.ipynb 12
def create_cropped_images(session, 
                        serfiq = None
                ):
        
        all_detectors = (session.query(Detector).all())
        for det in all_detectors:

            # Load SERFIQ model if neccesary
            if det.name == 'mtcnn_serfiq':
                
                fill_cropped_image = fill_cropped_image_serfiq
            else:
                
                fill_cropped_image = fill_cropped_image_general

            subquery = session.query(CroppedImage.image_id) \
                .filter(CroppedImage.detectors == det)
            images = (
                session.query(Image)
                    .filter(Image.image_id.notin_(subquery))
                    .all()
            )

            for img in tqdm(images[:5], desc=f'TRIM Creating Cropped Images for detector {det.name}'):
                cropped_image = CroppedImage()
                cropped_image.images = img
                cropped_image.detectors = det
                fill_cropped_image(cropped_image, ser_fiq = serfiq)
                session.add(cropped_image)
                session.commit()

# %% ../nbs/02_alchemy.ipynb 13
def create_face_images(session):
        
    all_embedding_models = (session.query(EmbeddingModel).all())
    for emb in tqdm(all_embedding_models, desc='Embedding models'):
        subquery = session.query(FaceImage.croppedImage_id) \
            .filter(FaceImage.embeddingModels == emb)
        cropped_images = (
            session.query(CroppedImage) \
                .filter(CroppedImage.croppedImage_id.notin_(subquery),
                        CroppedImage.face_detected == True)
                .all()
        )

        for cr_img in tqdm(cropped_images, desc=f'Face images in {emb.name}'):
            face_image = FaceImage()
            face_image.croppedImages = cr_img
            face_image.embeddingModels = emb
            session.add(face_image)
            session.commit()

# %% ../nbs/02_alchemy.ipynb 14
def create_quality_images(session):
        
        all_quality_models = (session.query(QualityModel).all())
        for qua in tqdm(all_quality_models, desc='Quality models'):
            subquery = session.query(QualityImage.faceImage_id) \
                .filter(QualityImage.qualityModels == qua)
            face_images = (
                session.query(FaceImage) \
                    .filter(FaceImage.faceImage_id.notin_(subquery))
                    .all()
            )

            for face_img in tqdm(face_images, desc=f'Quality images in {qua.name}'):
                qua_image = QualityImage()
                qua_image.faceImages = face_img
                qua_image.qualityModels = qua
                session.add(qua_image)
                session.commit()

# %% ../nbs/02_alchemy.ipynb 16
def update_gender(session, databases:List[FaceDataBase], force_update: bool = False):
    for db in databases:
        query = session.query(Image).filter(Image.source == db.source)
        if not force_update:
            query = query.filter(Image.gender == None)
        all_img = (query.all())
        for img in tqdm(all_img[:10], desc='TRIM Update gender'):
            filters = DeepFace.analyze(img_path=img.get_image(), actions=[
                                       'gender'], enforce_detection=False)
            img.gender = Gender(filters["gender"])
            session.commit()

# %% ../nbs/02_alchemy.ipynb 17
def update_age(session, databases:List[FaceDataBase],force_update: bool = False):
    for db in databases:
        query = session.query(Image).filter(Image.source == db.source)
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

# %% ../nbs/02_alchemy.ipynb 18
def update_emotion(session, databases:List[FaceDataBase],force_update: bool = False):
    for db in databases:
        query = session.query(Image).filter(Image.source == db.source)
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

# %% ../nbs/02_alchemy.ipynb 19
def update_race(session, databases:List[FaceDataBase], force_update: bool = False):
    for db in databases:
        query = session.query(Image).filter(Image.source == db.source)
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

# %% ../nbs/02_alchemy.ipynb 20
def update_images(session, 
                databases:List[FaceDataBase], 
                attributes: List[str], 
                force_update: bool = False
                ):

    "Updates Image attributes"
    if 'gender' in attributes:
        update_gender(session, databases, force_update)

    if 'age' in attributes:
        update_age(session, databases, force_update)

    if 'emotion' in attributes:
        update_emotion(session, databases, force_update)
    
    if 'race' in attributes:
        update_race(session, databases, force_update) 

# %% ../nbs/02_alchemy.ipynb 22
def update_cropped_images(session, force_update: bool = False, serfiq = None):
        
    query = session.query(CroppedImage).join(Detector)
    
    if not force_update:
        query = query.filter(or_(CroppedImage.face_detected == None, CroppedImage.bounding_box == None))

    query_serfiq = query.filter(Detector.name == 'mtcnn_serfiq')
    query_general = query.filter(Detector.name != 'mtcnn_serfiq')

    all_cr_img_serfiq = (query_serfiq.all())
    all_cr_img_general = (query_general.all())

    
    if all_cr_img_serfiq:
        # ser_fiq = serfiq
        fill_cropped_image = fill_cropped_image_serfiq
        for cr_img in tqdm(all_cr_img_serfiq, desc='Update cropped images serfiq'):
            fill_cropped_image(cr_img, ser_fiq = serfiq)
            session.commit()

    # ser_fiq = None
    fill_cropped_image = fill_cropped_image_general

    for cr_img in tqdm(all_cr_img_general, desc='Update cropped images'):
        fill_cropped_image(cr_img, ser_fiq = serfiq)
        session.commit()


# %% ../nbs/02_alchemy.ipynb 23
def update_face_images(session, force_update: bool = False):
    update_embeddings(session, force_update)
# self.update_confusion_score(force_update)

# %% ../nbs/02_alchemy.ipynb 24
def update_embeddings(session, force_update: bool = False):
    
    query = session.query(FaceImage, EmbeddingModel, Detector, Image) \
        .join(EmbeddingModel) \
        .join(CroppedImage, CroppedImage.croppedImage_id == FaceImage.croppedImage_id) \
        .join(Detector) \
        .join(Image, Image.image_id == CroppedImage.image_id) \
        .filter(EmbeddingModel.name != 'FaceVACs', Detector.name != 'mtcnn_serfiq')

    if not force_update:
        query = query.filter(FaceImage.embeddings == None)
    all_face_img = (query.all())

    for face_img in tqdm(all_face_img, desc='Computing embeddings'):
        embedding = DeepFace.represent(face_img.Image.get_image(), detector_backend=face_img.Detector.name,
                                        model_name=face_img.EmbeddingModel.name, enforce_detection=True)
        face_img.FaceImage.embeddings = embedding

        session.commit()

# %% ../nbs/02_alchemy.ipynb 25
def update_quality_images(session, serfiq=None, force_update: bool = False):
    
    # update_ser_fiq(session, serfiq = serfiq, force_update=force_update)
    update_tface(session, serfiq = serfiq, force_update=force_update)         

# %% ../nbs/02_alchemy.ipynb 26
def update_ser_fiq(session, serfiq = None, force_update: bool = False):
    
    # todo: Now it is only for ArcFace, it should be expanded to other embedding models.
    query = session.query(QualityImage, CroppedImage) \
        .join(QualityModel) \
        .join(FaceImage, FaceImage.faceImage_id == QualityImage.faceImage_id) \
        .join(EmbeddingModel) \
        .join(CroppedImage, CroppedImage.croppedImage_id == FaceImage.croppedImage_id) \
        .filter(EmbeddingModel.name == 'ArcFace',
                QualityModel.name == 'ser_fiq')
    #    .join(Image, Image.image_id == CroppedImage.image_id) \
    #    

    if not force_update:
        query = query.filter(QualityImage.quality == None)
    all_rows = (query.all())

    for row in tqdm(all_rows[:5], desc='TRIM Computing SER-FIQ quality'):              

        aligned_img = row.CroppedImage.get_aligned_image(ser_fiq=serfiq) 
        quality = serfiq.get_score(aligned_img, T=100)
        
        row.QualityImage.quality = quality
        session.commit()

# %% ../nbs/02_alchemy.ipynb 27
def update_tface(session, serfiq, force_update: bool = False):
    ser_fiq = serfiq

    net = get_network()

    # todo: Now it is only for ArcFace, it should be expanded to other embedding models. 
    # Is it ArcFace or another face recognition model?
    
    query = session.query(QualityImage, CroppedImage) \
        .join(QualityModel) \
        .join(FaceImage, FaceImage.faceImage_id == QualityImage.faceImage_id) \
        .join(EmbeddingModel) \
        .join(CroppedImage, CroppedImage.croppedImage_id == FaceImage.croppedImage_id) \
        .filter(EmbeddingModel.name == 'ArcFace', 
                QualityModel.name == 'tface')
        # .join(Image, Image.image_id == CroppedImage.image_id) 
        

    if not force_update:
        query = query.filter(QualityImage.quality == None)
    all_rows = (query.all())

    for row in tqdm(all_rows[:5], desc='TRIM: Computing TFace quality'):              

        aligned_img = row.CroppedImage.get_aligned_image(ser_fiq=serfiq) 
        quality = compute_tf_quality(aligned_img, net)             
        
        row.QualityImage.quality = quality
        session.commit()
