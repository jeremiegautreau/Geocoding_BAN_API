# -*- coding: utf-8 -*-

import requests
import csv
import os
from time import sleep
from io import StringIO
from qgis.PyQt.QtCore import QCoreApplication,  QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterField,
                       QgsVectorLayer, 
                       QgsField, 
                       QgsGeometry,
                       QgsPointXY,
                       QgsFeature,
                       QgsWkbTypes,
                       QgsCoordinateReferenceSystem,
                       QgsProcessingParameterFeatureSink)
from qgis import processing


def geocoding(csv_path, col_add, DEFAULT_REQUEST):
    
    url_api = 'https://api-adresse.data.gouv.fr/search/csv/'
    
    csv = open(csv_path, 'rb')
    
    files = [('data', csv),
            ('columns', (None, col_add[0]))
            ] + DEFAULT_REQUEST
            
    
    response = requests.post(url_api, files=files)
    
    csv.close()
    
    return response
    
class BAN_Geocoding(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    COL_ADD = 'COL_ADD'
    OPTIONS = 'OPTIONS'
    ADRESSE ='ADRESSE'
    
    

    def tr(self, string):

        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return BAN_Geocoding()

    def name(self):

        return 'BAN_Geocoding'

    def displayName(self):

        return self.tr('BAN Geocoding')

    def group(self):

        return self.tr('Geocoding')

    def groupId(self):

        return 'Geocoding'

    def shortHelpString(self):

        return self.tr("""Geocoding des adresses depuis la BAN:
        La couche d'entrée doit être un csv avec une colonne contenant l'adresse concaténée (rue + code postal + commune).
        L'algorithme transforme le fichier csv en une couche de point et ajoute les attributs: label (adresse formatée) et score (niveau de précision (%) pour chaque adresse).
        Option : il est possible de choisir des attributs supplémentaires renvoyés par l'API. La latitude et la longitude font partie de la requête de base mais doivent être sélectionnés pour apparaitre dans la table des attributs.
        Note: Cet algorithme est très inspiré par le code du plugin QBAN(O) réalisé par CREAGIS : https://github.com/CREASIG/QBANO.
        La documentation de l'API et les exemples python fournient par les équipes Etalab ont aussi permis la réalisation de cet algorithme : https://guides.etalab.gouv.fr/apis-geo/1-api-adresse.html#qu-est-ce-que-le-geocodage. 
        """)

    def initAlgorithm(self, config=None):
       
        #INPUT de la couche d'entrée (CSV des adresses).
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('CSV des adresses'),
                [QgsProcessing.TypeVector]
            )
        )
        
        #INPUT du choix des attributs en options
        #La fonction QgsProcessingParameterEnum renvoie un int
        #pour chaque options correspondant à l'ordre de l'élément dans la liste
        self.addParameter(QgsProcessingParameterEnum(
            self.OPTIONS,
            self.tr("Attributs supplémentaires"),
            options=[
                'result_type', 
                'result_id', 
                'result_housenumber', 
                'result_name', 
                'result_street',
                'result_postcode',
                'result_city',
                'result_context',
                'result_citycode',
                'result_oldcitycode',
                'result_oldcity',
                'result_district',
                'latitude',
                'longitude'
            ],
            allowMultiple=True,
            optional=True
            )
        )
            
        #INPUT de la colonne contenant l'adresse
        self.addParameter(
            QgsProcessingParameterField(
                self.ADRESSE,
                self.tr("Colonne pour l'adresse"),
                defaultValue="NULL",
                parentLayerParameterName=self.INPUT,
                optional=False
            )
        )
            
        #OUTPUT retournant la couche de points géocodée.
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Geocoded')
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        """
        Fonction pour le traitement des données: 
        gécoding et transformation de la réponse en couche de points.
        """
        
        #Paramètre de la couche d'entrée pour récupérer les attributs du csv.
        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )
        
        #Paramètre de la couche d'entrée pour récupérer le chemin du csv.
        path = self.parameterAsVectorLayer(
            parameters,
            self.INPUT,
            context
        )
        
        #Paramètre pour renvoyer la liste des int correspondant aux options
        option = self.parameterAsEnums(
            parameters, 
            self.OPTIONS, 
            context
        )
        
        #Dictionnaire pour la correspondance des int avec les attributs opt
        option_dict = {
            0: 'result_type',
            1: 'result_id',
            2: 'result_housenumber',
            3: 'result_name',
            4: 'result_street',
            5: 'result_postcode',
            6: 'result_city',
            7: 'result_context',
            8: 'result_citycode',
            9:'result_oldcitycode',
            10: 'result_oldcity',
            11: 'result_district',
            12: 'latitude',
            13: 'longitude'
        }
                        
        
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
            
        csv_size = os.path.getsize(path.source()) # taille du fichier.
        #Vérification si la taille du csv ne dépasse pas 50Mo.
        #Si la limite est dépassée, le script s'arrête.
        if csv_size > 50000000:
            feedback.pushInfo("La taille du csv (" + str(os.path.getsize(path.source())/10**6)+ "Mo) est supérieur à la limite de 50Mo" )
            return {}
        
        #Création des colonnes (fields) pour la couche de sortie
        fields=source.fields() # récupération des colonnes du csv en entrée
        #Ajout de nouvelles colonnes pour la réponse de l'API
        fields.append(QgsField('label',QVariant.String,len=450)) or feedback.reportError('Le champs label existe deja, son contenu sera remplacé')
        fields.append(QgsField('score',QVariant.Double,len=10, prec=5)) or feedback.reportError('Le champs score existe deja, son contenu sera remplacé')
        
        
        #Requête de base pour l'API
        DEFAULT_REQUEST = [
        ('result_columns', (None, 'latitude')),
        ('result_columns', (None, 'longitude')),
        ('result_columns', (None, 'result_label')),
        ('result_columns', (None, 'result_score'))
        ]
        
        #Ajout des colonnes en options et modification de la requête à l'API
        if len(option)>0:
            for opt in option:
                if opt == 12 or opt == 13 :
                   fields.append(QgsField(option_dict[opt],QVariant.String,len=10)) or feedback.reportError('Le champs existe deja, son contenu sera remplacé') 
                else:
                    DEFAULT_REQUEST = DEFAULT_REQUEST + [('result_columns', (None, option_dict[opt]))]
                    fields.append(QgsField(option_dict[opt],QVariant.String,len=250)) or feedback.reportError('Le champs existe deja, son contenu sera remplacé')

        #Paramètre de sortie pour la couche de point 
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Point
         
        )
        
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
        
        #Paramètre pour récupérer la colonne contenant l'adresse
        col_add = self.parameterAsFields(
            parameters,
            self.ADRESSE,
            context
        )
        
        feedback.pushInfo("Colonne choisi pour l'adresse :" + str(col_add))
        
        csv_path = path.source()
        
        #Géocoding des adresses
        response = geocoding(csv_path, col_add, DEFAULT_REQUEST)
        
        feedback.setProgress(30)

        if response.status_code == 200:
            status = 'Request successful'
            feedback.pushInfo(str(status))
            
            #transformation de la réponse en dictionnaires
            csv_reader = csv.DictReader(StringIO(response.text), dialect='unix', delimiter=';')
            data = [row for row in csv_reader]

            features = source.getFeatures()
            
            total = 70 / len(data)
            
            #Intégration des valeurs reçues comme attributs
            #dans la couche de sortie
            for current, feature in enumerate(features):
                if feedback.isCanceled():
                    break
                            
                attr=feature.attributes()
                
                for i in range(fields.count()-len(attr)):
                    attr.append(None)
                feature.setFields(fields)
                feature.setAttributes(attr)
                feature.setAttribute('label',data[current]['result_label'])
                score = data[current]['result_score']
                if score == "":
                    feature.setAttribute('score',0)
                else:
                    feature.setAttribute('score',data[current]['result_score'])
                
                if len(option)>0:
                    for opt in option:
                        feature.setAttribute(option_dict[opt],data[current][option_dict[opt]])
                
                #Création de la géométrie avec la longitude et la latitude.
                try:
                    x = data[current]['longitude']
                    y = data[current]['latitude']
                    fx = float(x)
                    fy = float(y)
                    geom=QgsGeometry().fromPointXY(QgsPointXY(fx,fy))
                    feature.setGeometry(geom)
                except ValueError:
                    feedback.pushInfo("Ligne n° "+ str(current+1) + ", Le géocoding a échoué ! ")
                
                #Intégration des attributs dans la couche de sortie
                sink.addFeature(feature, QgsFeatureSink.FastInsert)
                sleep(0.11)
                
                feedback.setProgress(30 + int(current * total))
        
        else:
            #Si l'appel à l'API échoue, le script s'arrête.
            status = 'Error during request to API: ' + str(response.status_code)
            feedback.pushInfo(str(status))

        return {self.OUTPUT: dest_id}

