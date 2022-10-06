# PLS
## Partial least squares regression
 This procedure estimates partial least squares (PLS, also known as "projection to latent structure") regression models. PLS is a predictive technique that is an alternative to ordinary least squares (OLS) regression, canonical correlation, or structural equation modeling, and it is particularly useful when predictor variables are highly correlated or when the number of predictors exceeds the number of cases. 

---
Installation intructions
----
1. Open IBM SPSS Statistics
2. Navigate to Utilities -> Extension Bundles -> Download and Install Extension Bundles
3. Search for the name of the extension and click Ok. Your extension will be available.

---
Tutorial
----

### Installation Location

Analyze →

&nbsp;&nbsp;Regression →

&nbsp;&nbsp;&nbsp;&nbsp;Partial Least Squares 

### UI
<img width="893" alt="image" src="https://user-images.githubusercontent.com/19230800/194358120-9c3cfbba-981d-451a-802c-98a4abb021a0.png">
<img width="893" alt="image" src="https://user-images.githubusercontent.com/19230800/194358212-65dbc501-68af-4b55-996f-48acfe7b606f.png">
<img width="893" alt="image" src="https://user-images.githubusercontent.com/19230800/194358256-a733f3ee-0ceb-42ef-bc5a-d3ecd92d6747.png">

### Syntax
Example:

GET FILE "Employee Data".
PLS salary MLEVEL=S WITH salbegin jobtime prevexp
  /ID VARIABLE=id
  /CRITERIA LATENTFACTORS=5
  /MODEL salbegin jobtime prevexp salbegin*jobtime 
  /OUTDATASET LATENTFACTORS=latent_factors.

### Output
<img width="1067" alt="image" src="https://user-images.githubusercontent.com/19230800/194359007-d7b16255-d297-4e0b-9cee-47fa3f4db38e.png">
<img width="1247" alt="image" src="https://user-images.githubusercontent.com/19230800/194359090-caf2d75e-abef-4f77-9e3a-598c9c80a966.png">
<img width="1247" alt="image" src="https://user-images.githubusercontent.com/19230800/194359144-6e1ef5fe-111f-4da4-879b-07dad42b2947.png">


---
License
----

- Apache 2.0
                              
Contributors
----

  - IBM SPSS JKP, JMB
