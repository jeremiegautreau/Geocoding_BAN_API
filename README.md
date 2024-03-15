# Geocoding_BAN_API

The aims of the project was to try the pyQGIS library, create a geocoding algorithm using BAN(Base d'Adresse Nationale) API and render it accessible from the model designer.  
The model designer in QGIS allow to easily create GIS data processing automation.  
I used the [BAN API documentation](https://guides.etalab.gouv.fr/apis-geo/1-api-adresse.html#qu-est-ce-que-le-geocodage.) and the great work of CREAGIS with the [QBANO project](https://github.com/CREASIG/QBANO) to create the algorithm.  
The pyQGIS library is very specific and I was able to overcome issues in reviewing different QGIS projects on Github.

The algorithm uses the CSV endpoint of BAN API and make a point layer with the coordinates for each adress.  
You must provide the full address in a single field and in a CSV file.

![image](https://github.com/jeremiegautreau/Geocoding_BAN_API/assets/126112031/0af688b5-72ab-4ee6-aeba-a560a6cc6dec)


The options allow you to choose the different fields available from the API to add in the attribute table.

![image](https://github.com/jeremiegautreau/Geocoding_BAN_API/assets/126112031/8243569e-aa2a-4bde-b202-3c9e5e2dc4b6)

A precision score from the API is automatically added to assess the performance on each adress.







