from atlassian import Confluence
import json
from bs4 import BeautifulSoup
import pandas as pd
from jira import JIRA
import copy

class JiraIssue:
    def __init__(self, issueKey, issueType, userStoryKey, summary, labels, components, testType, testScope,
                  executionMode, automationCandidate, regression, testPriority, testReviewed, description, preRequisites,
                  dataset, procedure, expectedResult, project, fixVersion):
        self.issueKey = issueKey
        self.issueType = {'name': issueType}
        self.userStoryKey = userStoryKey
        self.summary = summary
        self.labels = convertStringToArray(labels)
        self.components = convertArrayToComponentList('name', convertStringToArray(components))
        self.testType = {'value': testType}
        self.testScope =convertArrayToComponentList('value', convertStringToArray(testScope))
        self.executionMode = {'value': executionMode}
        self.automationCandidate = {'value': automationCandidate}
        self.regression = {'value': regression}
        self.testPriority = {'value': testPriority}
        self.testReviewed = {'value': testReviewed}
        self.description = description
        self.preRequisites = preRequisites
        self.dataset = dataset
        self.procedure = procedure
        self.expectedResult = expectedResult
        self.project = {'key': project}
        self.fixVersion = fixVersion

# Asigna cada valor al campo correspondiente en Jira.
# Parametros: 
# jiraIssue (JiraIssue): variable instanciada de la clase JiraIssue.
# Retorna: 
# Diccionario [Key = Campo de Jira] [Valor = Valor correspondiente al campo]
def createIssueDict(jiraIssue):
    issueDict = {
        'project'          : jiraIssue.project,
        'issuetype'        : jiraIssue.issueType,
        'summary'          : jiraIssue.summary,
        'labels'           : jiraIssue.labels,
        'components'       : jiraIssue.components,
        'customfield_10101': jiraIssue.testType,
        'customfield_10163': jiraIssue.testScope,
        'customfield_10150': jiraIssue.executionMode,
        'customfield_10161': jiraIssue.automationCandidate,
        'customfield_10151': jiraIssue.regression,
        'customfield_10152': jiraIssue.testPriority,
        'customfield_10162': jiraIssue.testReviewed,
        'description'      : jiraIssue.description,
        'customfield_10070': jiraIssue.preRequisites,
        'customfield_10153': jiraIssue.dataset,
        'customfield_10071': jiraIssue.procedure,
        'customfield_10072': jiraIssue.expectedResult,
        'fixVersions': jiraIssue.fixVersion
    }
    return issueDict

def cargarJson(archivo):
    with open(archivo, 'r') as f:
        return json.load(f)
    
# Crea la conexión con Jira
# Parametros:
# Options(diccionario): {'server': 'url'}
# JIRAuser(str): usuario de Jira
# JIRApass(str): contraseña de Jira
def jiraConnection(options, JIRAuser, JIRApass):
    jira = JIRA(options, basic_auth=(JIRAuser, JIRApass))
    return jira

confluence = Confluence(
    url='https://confluence.tid.es/',
    username="qasupport",
    password="temporal",
    cloud=True)

componentName = "Android"

nombre_claves_ZABBIX = {
    "PATTERN TO SEARCH": "patternToSearch",
    "SEVERITY": "severity",
    "ALARM NAME": "alarmName",
    "ALARM TEXT": "alarmText",
    "CONDITION": "condition",
    "ACTION": "action",
    "Test Case ID": "Test Case ID"
}

listaIssueKibana = []

# Obtiene información de confluence correspondiente a la monitorización
# Parametros:
# monitorizacion(str): tipo de monitorización
# contenido(str): Contenido de la página HTML
# referencia(str): Delimitador que diferencia el contenido que queremos obtener
# Retorna: 
# Lista con todas la informacion obtenida 
def obtenerTextoConf(monitorizacion,contenido,referencia,modificar):
    match monitorizacion:
        case 'ZABBIX':
            listaZabbix = []
            contenidoSplit = contenido.split(referencia)
            html_completo = f"<table>{contenidoSplit[1]}</table>"
            soup = BeautifulSoup(html_completo, 'html.parser')
            table = soup.find('table')
            df = pd.read_html(str(table))[0]
            columnas_deseadas = ['PATTERN TO SEARCH', 'SEVERITY','ALARM NAME','ALARM TEXT','CONDITION','ACTION','Test Case ID']
            df_seleccionado = df[columnas_deseadas]
            if modificar == False:
                for index, fila in df_seleccionado.iterrows():
                    fila_dict = fila.to_dict()
                    if pd.isnull(fila_dict['Test Case ID']):
                        if 'Recuperación' in str(fila_dict['CONDITION']):
                            condition= str(fila_dict['CONDITION']).split('Recuperación')
                            fila_dict['CONDITION'] = {}
                            fila_dict['CONDITION']['alarm'] = condition[0]
                            fila_dict['CONDITION']['recovery'] = condition[1]
                        else:
                            condition= str(fila_dict['CONDITION']).split('Reactivar')
                            fila_dict['CONDITION'] = {}
                            fila_dict['CONDITION']['alarm'] = condition[0]
                            fila_dict['CONDITION']['recovery'] = condition[1]

                        #nuevo_data = {nombre_claves_ZABBIX[old_key]: value for old_key, value in fila_dict.items()}
                        nuevo_data = {nombre_claves_ZABBIX[old_key]: value for old_key, value in fila_dict.items() if old_key in nombre_claves_ZABBIX and not pd.isna(value)}
                        listaZabbix.append(nuevo_data)
            
            elif modificar == True:
                for index, fila in df_seleccionado.iterrows():
                    fila_dict = fila.to_dict()
                    if 'Recuperación' in str(fila_dict['CONDITION']):
                        condition = str(fila_dict['CONDITION']).split('Recuperación')
                        fila_dict['CONDITION'] = {}
                        fila_dict['CONDITION']['alarm'] = condition[0]
                        fila_dict['CONDITION']['recovery'] = condition[1]
                    else:
                        condition= str(fila_dict['CONDITION']).split('Reactivar')
                        fila_dict['CONDITION'] = {}
                        fila_dict['CONDITION']['alarm'] = condition[0]
                        fila_dict['CONDITION']['recovery'] = condition[1]

                    if pd.isna(fila_dict['Test Case ID']):
                        fila_dict['Test Case ID'] = " "
    
                    nuevo_data = {nombre_claves_ZABBIX[old_key]: value for old_key, value in fila_dict.items() if old_key in nombre_claves_ZABBIX and not pd.isna(value)}
    
                    if 'Test Case ID' in nombre_claves_ZABBIX and not pd.isna(fila_dict['Test Case ID']):
                        nuevo_data[nombre_claves_ZABBIX['Test Case ID']] = fila_dict['Test Case ID']
    
                    listaZabbix.append(nuevo_data)
            return listaZabbix
        
        case 'GRAFANA PLATFORM':
            listaGrafana = []
            contenidoSplit = contenido.split(referencia)
            soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
            table = soup.find('table')
            df = pd.read_html(str(table))[0]  
            df = df.drop(df.index[0])
            columnas_deseadas = [2,4,5,6,7]
            df_seleccionado = df[columnas_deseadas]

            if modificar == False:
                for index, fila in df_seleccionado.iterrows():
                    fila_dict = fila.to_dict()
                    if not pd.isnull(fila_dict[2]) and not pd.isnull(fila_dict[4]) and not pd.isnull(fila_dict[5]) and not pd.isnull(fila_dict[6]):
                        nuevo_data = {
                            "Metric": fila_dict[2],
                            "DB en Influx": fila_dict[4],
                            "Medida": fila_dict[5],
                            "Metrica": fila_dict[6],
                            "Test Case ID": fila_dict[7]
                        }
                        listaGrafana.append(nuevo_data)
            elif modificar == True:
                for index, fila in df_seleccionado.iterrows():
                    fila_dict = fila.to_dict()
                    if not pd.isnull(fila_dict[2]) and not pd.isnull(fila_dict[4]) and not pd.isnull(fila_dict[5]) and not pd.isnull(fila_dict[6]):
                        if pd.isna(fila_dict[7]):
                            fila_dict[7] = " "
                        nuevo_data = {
                            "Metric": fila_dict[2],
                            "DB en Influx": fila_dict[4],
                            "Medida": fila_dict[5],
                            "Metrica": fila_dict[6],
                            "Test Case ID": fila_dict[7]
                        }
                        listaGrafana.append(nuevo_data)
            primerElemento = listaGrafana.pop(0)
            return listaGrafana
        
        case 'GRAFANA PROMETHEUS':
            listaGrafana = []
            contenidoSplit = contenido.split(referencia)
            html_con_saltos = contenidoSplit[1].replace('<p>', '<p><br>')
            soup = BeautifulSoup(html_con_saltos, 'html.parser')
            table = soup.find('table')
            df = pd.read_html(str(table))[0]  
            columnas_deseadas = ['Metric', 'Type','DB En Influx','Medida','Métrica','Test Case ID']
            df_seleccionado = df[columnas_deseadas]

            if modificar == False:
                for index, fila in df_seleccionado.iterrows():
                    fila_dict = fila.to_dict()
                    if pd.isnull(fila_dict['Test Case ID']):
                        fila_dict['Métrica'] = fila_dict['Métrica'].replace(' ', '\n')
                        listaGrafana.append(fila_dict)
            elif modificar == True:
                for index, fila in df_seleccionado.iterrows():
                    fila_dict = fila.to_dict()
                    fila_dict['Métrica'] = fila_dict['Métrica'].replace(' ', '\n')
                    listaGrafana.append(fila_dict)
            return listaGrafana
        
        case 'KIBANA':
            listaKibana = []
            contenidoSplit = contenido.split(referencia)
            soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
            table = soup.find_all('table')
            tablas  = pd.read_html(str(table))
            if len(tablas) % 2 != 0:
                raise AssertionError(f"El numero de tablas es impar: {len(tablas)}")
            
            for i in range(0,len(tablas)):
                listaKibana.append(tablas[i].to_dict(orient='records'))
            return listaKibana

def escribirJson(nombreF,contenido):
    with open(nombreF, "w") as archivo:
            json.dump(contenido, archivo,indent=4)

def conversorJson(procedure):
    return "*GIVEN* "+procedure["GIVEN"]+ "\n*WHEN* "+procedure["WHEN"]+"\n*AND* "+procedure["AND"]+"\n*THEN* "+procedure["THEN"]

# Crea el título del TC
# Parámetros:
# monitorizacion(str): tipo de monitorización
# datosFijos(diccionario): Datos obtenidos del JSON datosFijos.json
# datoConfluence(lista): Datos obtenidos de Confluence (obtenerTextoConf)
def createSummary(monitorizacion,datosFijos,datoConfluence):
    match monitorizacion:
        case 'ZABBIX':
            return "["+datosFijos[monitorizacion]["Monitorizacion"]+"] ["+componentName+"] - "+datoConfluence["severity"]+" - "+datoConfluence["alarmName"]
        case 'GRAFANA PLATFORM':
            return "["+datosFijos[monitorizacion]["Monitorizacion"]+"] ["+componentName+"] - PLATFORM METRICS - "+datoConfluence["Metric"]
        case 'GRAFANA PROMETHEUS':
            return "["+datosFijos[monitorizacion]["Monitorizacion"]+"] ["+componentName+"] - PROMETHEUS METRICS - "+datoConfluence["Metric"]
        case 'KIBANA':
            return "["+datosFijos[monitorizacion]["Monitorizacion"]+"] ["+componentName+"] - "+datoConfluence[0][0]['functionName']+" fields mapping using index "+datoConfluence[0][0]["indice"]

def convertStringToArray(stringData):
    arrayData = str(stringData).replace(" ", "").split(',')
    return arrayData

def convertStringToArrayWithoutSplit(stringData):
    arrayData = str(stringData).split(',')
    return arrayData

def convertArrayToComponentList(nameField, array):
    valueListComponent = []
    for elementArray in array:
        if elementArray == "":
            valueListComponent.append({nameField: None})
        else:
            valueListComponent.append({nameField: elementArray})
    return valueListComponent

# Actualiza la información obtenida del JSON datosFijos.json con la información obtenida de confluence
# Parámetros:
# monitorizacion(str): tipo de monitorización
# datosFijos(diccionario): Datos obtenidos del JSON datosFijos.json
# datoConfluence(lista): Datos obtenidos de Confluence (obtenerTextoConf)
def actualizarDatosFijos(monitorizacion,datosConf,datosFijos):

    match monitorizacion:
        case 'ZABBIX':
            alarmName = datosConf['alarmName']
            severity = datosConf['severity']
            alarmName = datosConf['alarmName']
            alarmText = datosConf['alarmText']
            action = datosConf['action']
            patternToSearch = datosConf['patternToSearch']
            condition = datosConf['condition']['alarm']
            recovery = datosConf['condition']['recovery']

            datosFijos[monitorizacion]['Procedure']['AND'] = datosFijos[monitorizacion]['Procedure']['AND'].replace('ALARMNAME',alarmName)
            datosFijos[monitorizacion]['Procedure']['AND'] = datosFijos[monitorizacion]['Procedure']['AND'].replace('COMPONENTNAME',componentName)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace('SEVERITY',severity)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace('ALARMNAME',alarmName)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace('ALARMTEXT',alarmText)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace('ACTION',action)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('PATTERNTOSEARCH',patternToSearch)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('CONDITION',condition)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('RECOVERY',recovery)
            datosFijos[monitorizacion]['Procedure'] = conversorJson(datosFijos[monitorizacion]['Procedure'])
            
            return datosFijos
        
        case 'KIBANA':
            functionName = datosConf[0][0]['functionName']
            cont = ""

            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace("FUNCTIONNAME",functionName)
            for i in datosConf[1]:
                    cont = cont +"\n|"+str(i['Update'])+"|"+str(i["Release top.catalog.conversor"])+"|"+str(i["Field"])+"|"+str(i["Name"])+"|"+str(i["Type"])+"|"+str(i["Description"])+"|"+str(i["Required in Kibana"])+"|"+str(i["Example"])+"|"
                    cont = cont.replace("nan"," ")
                    
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace("CONTENT",cont)
            return datosFijos

        case 'GRAFANA PLATFORM':
            dbInflux = datosConf['DB en Influx']
            medida = datosConf['Medida']
            metrica = datosConf['Metrica']
            
            datosFijos[monitorizacion]['PreRequisites'] = datosFijos[monitorizacion]['PreRequisites'].replace('DBINFLUX',dbInflux)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('MEDIDA',medida)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('POD',componentName)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('METRICA',metrica)

            return datosFijos
        
        case 'GRAFANA PROMETHEUS':
            dbInflux = datosConf['DB En Influx']
            medida = datosConf['Medida']
            metrica = datosConf['Métrica']
            type = datosConf['Type']
            datosFijos[monitorizacion]['PreRequisites'] = datosFijos[monitorizacion]['PreRequisites'].replace('DBINFLUX',dbInflux)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('MEDIDA',medida)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('METRIC',componentName)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('M\u00e9trica',metrica)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace('TYPE',type)

            return datosFijos


def buscar_ticket_existente(jira, busqueda,criterio_busqueda):
    criterio_busqueda = criterio_busqueda.replace('"', '\\"')
    query = f'summary ~ "\\"{criterio_busqueda}\\""'
    issues = jira.search_issues(query)
    return issues[0] if issues else None

def buscar_ticket_existente_por_key(jira, key):
    try:
        issue = jira.issue(key)
        return issue
    except Exception as e:
        return None

# Crea Test Case en Jira
# Parámetros:
# monitorizacion(str): tipo de monitorización
# datoConfluence(lista): Datos obtenidos de Confluence (obtenerTextoConf)
def creaJira(project,monitorizacion,datosConfluence,modificar,componente,label=None,fixVersion=None):
    options = {'server': 'https://jira.tid.es/'}
    userJira = 'qasupport'
    passJIRA = 'temporal'
    jira = jiraConnection(options, userJira, passJIRA)

    match monitorizacion:

        case 'ZABBIX':
            listaIssueZabbix = []
            for dato in datosConfluence:
                datosFijos = cargarJson('datosFijos.json')
                datosFijos = actualizarDatosFijos(monitorizacion,dato,datosFijos)

                x = fixVersion.split(",")
                y = []
                for i in x:
                    temporal = {'name':i}
                    y.append(temporal)
                
                for z in y:
                    print (z)

                jiraIssue = JiraIssue("","Test Case","",createSummary(monitorizacion,datosFijos,dato),label,componente,datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'],datosFijos[monitorizacion]['ExecutionMode'],datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'],datosFijos[monitorizacion]['TestPriority'],datosFijos[monitorizacion]['TestReviewed'],
                                    "",datosFijos[monitorizacion]['PreRequisites'],datosFijos[monitorizacion]['DataSet'],
                                    datosFijos[monitorizacion]['Procedure'],datosFijos[monitorizacion]['ExpectedResult'],project,y)
                
                if modificar == True:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(f'Ticket {ticket_existente.key} actualizado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueZabbix.append(ticket_existente)
                    else:
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueZabbix.append(str(jiraIssue.issueKey))
                
                elif modificar == False:
                        print (jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        listaIssueZabbix.append(str(jiraIssue.issueKey))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print (jiraIssue.issueKey)

            modificarTesCaseId(listaIssueZabbix,'ZABBIX',modificar)
                
            
        case 'GRAFANA PLATFORM':
            listaIssueGrafanaPlatform = []
            for dato in datosConfluence:
                datosFijos = cargarJson('datosFijos.json')
                datosFijos = actualizarDatosFijos(monitorizacion,dato,datosFijos)
                jiraIssue = JiraIssue("","Test Case","",createSummary(monitorizacion,datosFijos,dato),label,componente,datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'],datosFijos[monitorizacion]['ExecutionMode'],datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'],datosFijos[monitorizacion]['TestPriority'],datosFijos[monitorizacion]['TestReviewed'],
                                    datosFijos[monitorizacion]['Description'],datosFijos[monitorizacion]['PreRequisites'],datosFijos[monitorizacion]['DataSet'],
                                   "","",project,fixVersion)
                
                if modificar == True:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(f'Ticket {ticket_existente.key} actualizado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueGrafanaPlatform.append(ticket_existente)
                    else:
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueGrafanaPlatform.append(str(jiraIssue.issueKey))
                
                elif modificar == False:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        print ("TC EXISTENTE: "+str(key))
                    else:
                        print (jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        listaIssueGrafanaPlatform.append(str(jiraIssue.issueKey))
                        print (jiraIssue.issueKey)

            modificarTesCaseId(listaIssueGrafanaPlatform,'GRAFANA PLATFORM',modificar)

        case 'GRAFANA PROMETHEUS':
            listaIssueGrafanaPrometheus = []
            for dato in datosConfluence:
                datosFijos = cargarJson('datosFijos.json')
                datosFijos = actualizarDatosFijos(monitorizacion,dato,datosFijos)
                jiraIssue = JiraIssue("","Test Case","",createSummary(monitorizacion,datosFijos,dato),label,componente,datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'],datosFijos[monitorizacion]['ExecutionMode'],datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'],datosFijos[monitorizacion]['TestPriority'],datosFijos[monitorizacion]['TestReviewed'],
                                    datosFijos[monitorizacion]['Description'],datosFijos[monitorizacion]['PreRequisites'],datosFijos[monitorizacion]['DataSet'],
                                   "","",project,fixVersion)
                if modificar == True:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(f'Ticket {ticket_existente.key} actualizado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueGrafanaPrometheus.append(ticket_existente)
                    else:
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueGrafanaPrometheus.append(str(jiraIssue.issueKey))
                
                elif modificar == False:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        print ("TC EXISTENTE: "+str(key))
                    else:
                        print (jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        listaIssueGrafanaPrometheus.append(str(jiraIssue.issueKey))
                        print (jiraIssue.issueKey)

            modificarTesCaseId(listaIssueGrafanaPrometheus,'GRAFANA PROMETHEUS',modificar)
        
        case 'KIBANA':
                datosFijos = cargarJson('datosFijos.json')
                datosFijos = actualizarDatosFijos(monitorizacion,datosConfluence,datosFijos)
                jiraIssue = JiraIssue("","Test Case","",createSummary(monitorizacion,datosFijos,datosConfluence),label,componente,datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'],datosFijos[monitorizacion]['ExecutionMode'],datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'],datosFijos[monitorizacion]['TestPriority'],datosFijos[monitorizacion]['TestReviewed'],
                                    "","",datosFijos[monitorizacion]['DataSet'],
                                   "",datosFijos[monitorizacion]['ExpectedResult'],project,fixVersion)
                
                if modificar == True:
                    key = datosConfluence[0][0]['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(f'Ticket {ticket_existente.key} actualizado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueKibana.append(ticket_existente)
                    else:
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueKibana.append(str(jiraIssue.issueKey))
                
                elif modificar == False:
                    key = datosConfluence[0][0]['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        print ("TC EXISTENTE: "+str(key))
                    else:
                        print (jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(fields=createIssueDict(jiraIssue))
                        listaIssueKibana.append(str(jiraIssue.issueKey))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print (jiraIssue.issueKey)

def crearJson(diccionario,archivo):
    with open(archivo, 'w') as file:
        json.dump(diccionario, file, indent=4)

def obtenerTable(space,title,referencia):
    page2 = confluence.get_page_by_title(space, title, expand='body.storage')
    contenido = page2['body']['storage']['value']
    contenidoSplit = contenido.split(referencia)
    soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
    table = soup.find('table')
    return table

def actualizarConfluence(titulo,page,htmlActualizado,comentario):
    status = confluence.update_page(
                        page_id=page['id'],
                        title=titulo,
                        body=htmlActualizado,
                        version_comment=comentario
                    )
    if status:
        print('Página actualizada exitosamente')
    else:
        print('Error al actualizar la página')

def modificarTesCaseId(key,monitorizacion,modificar):

    match monitorizacion:
        case 'ZABBIX':
            space='QAVIDEO'
            title='pruebas QA'
            page = confluence.get_page_by_title(space, title)
            if page:
                page2 = confluence.get_page_by_title(space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')
                tablas = contenido_completo_soup.find_all('table')
                if modificar == False:
                    indiceTabla = 12
                    if indiceTabla < len(tablas):
                        table = tablas[indiceTabla]

                        frase = "3.2.3 PARSEO DE ARCHIVOS DE LOG PARA MONITORIZACIÓN"
                        frase_tag = contenido_completo_soup.find(string=frase)
                        tabla_despues_de_frase = None
                        if frase_tag:
                            siguiente_elemento = frase_tag.find_next()
                            while siguiente_elemento:
                                if siguiente_elemento.name == 'table':
                                    tabla_despues_de_frase = siguiente_elemento
                                    break
                                siguiente_elemento = siguiente_elemento.find_next()

                        if tabla_despues_de_frase:
                            indice_tabla = tablas.index(tabla_despues_de_frase)

                        indice_tabla_a_actualizar = indice_tabla
                        tabla_original = tablas[indice_tabla_a_actualizar]
                        primer_tr_original = tabla_original.find('tr')
                        primer_tr_copy = copy.deepcopy(primer_tr_original)

                        first_tr = table.find('tr')
                        if first_tr:
                            first_tr.decompose()

                        df = pd.read_html(str(table))[0]         
                        columnas_deseadas = ['Test Case ID']           
                        df_seleccionado = df[columnas_deseadas]
                        contador = 0
                        fila_dict = {}
                        for index, fila in df_seleccionado.iterrows():
                            if pd.isnull(fila['Test Case ID']) or fila['Test Case ID'] == "":
                                fila_dict = fila.to_dict()
                                fila_dict['Test Case ID'] = key[contador]
                                df.at[index, 0] = fila_dict['Test Case ID']  
                                contador = contador + 1

                        data_actualizada = df.values.tolist()

                        filas = table.find_all('tr')
                        for i, fila in enumerate(filas[1:], start=1):  
                            celdas = fila.find_all('td')
                            for j, celda in enumerate(celdas):
                                if j == 12:
                                    celda_valor = celda.get_text(strip=True)
                                    if pd.isnull(celda_valor) or celda_valor == "":
                                        celda.string = str(data_actualizada[i-1][j+1])
                            
                        tabla_html_actualizada = str(table)
                            
                        if indice_tabla_a_actualizar < len(tablas):
                            tabla_html_actualizada = BeautifulSoup(tabla_html_actualizada, 'html.parser')
                            filas_actualizadas = tabla_html_actualizada.find_all('tr')
                            tabla_original.clear()
                            tabla_original.append(primer_tr_copy)
                            for fila in filas_actualizadas:
                                tabla_original.append(fila)
                            tablas[indice_tabla_a_actualizar].replace_with(tabla_original)
                        html_completo_actualizado = str(contenido_completo_soup)

                elif modificar == True:
                    indiceTabla = 12
                    if indiceTabla < len(tablas):
                        table = tablas[indiceTabla]

                        frase = "3.2.3 PARSEO DE ARCHIVOS DE LOG PARA MONITORIZACIÓN"
                        frase_tag = contenido_completo_soup.find(string=frase)
                        tabla_despues_de_frase = None
                        if frase_tag:
                            siguiente_elemento = frase_tag.find_next()
                            while siguiente_elemento:
                                if siguiente_elemento.name == 'table':
                                    tabla_despues_de_frase = siguiente_elemento
                                    break
                                siguiente_elemento = siguiente_elemento.find_next()

                        if tabla_despues_de_frase:
                            indice_tabla = tablas.index(tabla_despues_de_frase)

                        indice_tabla_a_actualizar = indice_tabla
                        tabla_original = tablas[indice_tabla_a_actualizar]
                        primer_tr_original = tabla_original.find('tr')
                        primer_tr_copy = copy.deepcopy(primer_tr_original)

                        first_tr = table.find('tr')
                        if first_tr:
                            first_tr.decompose()

                        df = pd.read_html(str(table))[0]         
                        columnas_deseadas = ['Test Case ID']           
                        df_seleccionado = df[columnas_deseadas]
                        contador = 0
                        fila_dict = {}
                        for index, fila in df_seleccionado.iterrows():
                            fila_dict = fila.to_dict()
                            fila_dict['Test Case ID'] = key[contador]
                            df.at[index, 0] = fila_dict['Test Case ID']  
                            contador = contador + 1

                        data_actualizada = df.values.tolist()

                        filas = table.find_all('tr')
                        for i, fila in enumerate(filas[1:], start=1):  
                            celdas = fila.find_all('td')
                            for j, celda in enumerate(celdas):
                                if j == 12:
                                    celda.string = str(data_actualizada[i-1][j+1])
                            
                        tabla_html_actualizada = str(table)
                            
                        if indice_tabla_a_actualizar < len(tablas):
                            tabla_html_actualizada = BeautifulSoup(tabla_html_actualizada, 'html.parser')
                            filas_actualizadas = tabla_html_actualizada.find_all('tr')
                            tabla_original.clear()
                            tabla_original.append(primer_tr_copy)
                            for fila in filas_actualizadas:
                                tabla_original.append(fila)
                            tablas[indice_tabla_a_actualizar].replace_with(tabla_original)
                        html_completo_actualizado = str(contenido_completo_soup)

                status = confluence.update_page(
                        page_id=page['id'],
                        title=title,
                        body=html_completo_actualizado,
                        version_comment='TC ZABBIX'
                    )
                if status:
                    print('Página actualizada exitosamente')
                else:
                    print('Error al actualizar la página')
                
        case 'GRAFANA PLATFORM':
            space='QAVIDEO'
            title='pruebas QA'
            page = confluence.get_page_by_title(space, title)
            if page:
                page2 = confluence.get_page_by_title(space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenidoSplit = contenido.split("Referencia Grafana Plataforma QA")
                soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
                table = soup.find('table')
                df = pd.read_html(str(table))[0]  
                df = df.drop(df.index[0])
                columnas_deseadas = [2,4,5,6,7]
                df_seleccionado = df[columnas_deseadas]
                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')
                tablas = contenido_completo_soup.find_all('table')
                if modificar == False:
                    contador = 0
                    frase = "Referencia Grafana Plataforma QA"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None
                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if tabla_despues_de_frase:
                        indice_tabla = tablas.index(tabla_despues_de_frase)

                    indice_tabla_a_actualizar = indice_tabla
                    for index, fila in df_seleccionado[1:].iterrows():
                        fila_dict = fila.to_dict()
                        if not pd.isnull(fila_dict[2]) and not pd.isnull(fila_dict[4]) and not pd.isnull(fila_dict[5]) and not pd.isnull(fila_dict[6]) and pd.isnull(fila_dict[7]):   
                            fila_dict[7] = key[contador]
                            df.at[index, 7] = fila_dict[7]  
                            contador = contador + 1

                    data_actualizada = df.values.tolist()
                    filas = table.find_all('tr')
                    for i, fila in enumerate(filas[1:], start=1):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j in columnas_deseadas:
                                #celda.string = str(data_actualizada[i-1][j])
                                nuevo_contenido = f"<strong>{data_actualizada[i-1][j]}</strong>"
                                celda.string = ''
                                celda.append(BeautifulSoup(nuevo_contenido, 'html.parser'))
                    
                    tabla_html_actualizada = str(table)
                    tabla_html_actualizada = tabla_html_actualizada.replace('nan', 'N/A')

                    if indice_tabla_a_actualizar < len(tablas):
                        tablas[indice_tabla_a_actualizar].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                    
                    
                    html_completo_actualizado = str(contenido_completo_soup)
                
                elif modificar == True:
                    contador = 0
                    frase = "Referencia Grafana Plataforma QA"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None
                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if tabla_despues_de_frase:
                        indice_tabla = tablas.index(tabla_despues_de_frase)

                    indice_tabla_a_actualizar = indice_tabla
                    for index, fila in df_seleccionado[1:].iterrows():
                        fila_dict = fila.to_dict()
                        if not pd.isnull(fila_dict[2]) and not pd.isnull(fila_dict[4]) and not pd.isnull(fila_dict[5]) and not pd.isnull(fila_dict[6]):   
                            fila_dict[7] = key[contador]
                            df.at[index, 7] = fila_dict[7]  
                            contador = contador + 1

                    data_actualizada = df.values.tolist()
                    filas = table.find_all('tr')
                    for i, fila in enumerate(filas[1:], start=1):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j in columnas_deseadas:
                                #celda.string = str(data_actualizada[i-1][j])
                                nuevo_contenido = f"<strong>{data_actualizada[i-1][j]}</strong>"
                                celda.string = ''
                                celda.append(BeautifulSoup(nuevo_contenido, 'html.parser'))
                    
                    tabla_html_actualizada = str(table)
                    tabla_html_actualizada = tabla_html_actualizada.replace('nan', 'N/A')

                    if indice_tabla_a_actualizar < len(tablas):
                        tablas[indice_tabla_a_actualizar].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                    
                    
                    html_completo_actualizado = str(contenido_completo_soup)
                status = confluence.update_page(
                        page_id=page['id'],
                        title=title,
                        body=html_completo_actualizado,
                        version_comment='TC Grafana Platform'
                    )
                if status:
                    print('Página actualizada exitosamente')
                else:
                    print('Error al actualizar la página')
        
        case 'GRAFANA PROMETHEUS':
            space='QAVIDEO'
            title='pruebas QA'
            page = confluence.get_page_by_title(space, title)
            if page:
                page2 = confluence.get_page_by_title(space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenidoSplit = contenido.split("Referencia GRAFANA PROMETHEUS QA")
                soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
                table = soup.find('table')
                df = pd.read_html(str(table))[0]  
                df = df.drop(df.index[0])
                columnas_deseadas = ['Test Case ID']
                df_seleccionado = df[columnas_deseadas]
                contador = 0
                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')
                tablas = contenido_completo_soup.find_all('table')
                if modificar == False:

                    frase = "Referencia GRAFANA PROMETHEUS QA"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None
                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if tabla_despues_de_frase:
                        indice_tabla = tablas.index(tabla_despues_de_frase)

                    indice_tabla_a_actualizar = indice_tabla
                    for index, fila in df_seleccionado.iterrows():
                        if pd.isnull(fila['Test Case ID']) or fila['Test Case ID'] == "":
                            fila_dict = fila.to_dict()
                            fila_dict['Test Case ID'] = key[contador]
                            df.at[index, 0] = fila_dict['Test Case ID']  
                            contador = contador + 1

                    data_actualizada = df.values.tolist()
                    filas = table.find_all('tr')
                    cont = 0
                    for i, fila in enumerate(filas): 
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 16:
                                celda_valor = celda.get_text(strip=True)
                                if pd.isnull(celda_valor) or celda_valor == "":
                                    celda.string = key[cont]
                                    cont = cont + 1
                    
                    tabla_html_actualizada = str(table)
                    if indice_tabla_a_actualizar < len(tablas):
                        tablas[indice_tabla_a_actualizar].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                    html_completo_actualizado = str(contenido_completo_soup)
                
                elif modificar == True:
                    frase = "Referencia GRAFANA PROMETHEUS QA"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None
                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if tabla_despues_de_frase:
                        indice_tabla = tablas.index(tabla_despues_de_frase)

                    indice_tabla_a_actualizar = indice_tabla
                    for index, fila in df_seleccionado.iterrows():
                        fila_dict = fila.to_dict()
                        fila_dict['Test Case ID'] = key[contador]
                        df.at[index, 0] = fila_dict['Test Case ID']  
                        contador = contador + 1

                    data_actualizada = df.values.tolist()
                    filas = table.find_all('tr')
                    cont = 0
                    for i, fila in enumerate(filas): 
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 16:
                                celda.string = str(key[cont])
                                cont = cont + 1
                    
                    tabla_html_actualizada = str(table)
                    if indice_tabla_a_actualizar < len(tablas):
                        tablas[indice_tabla_a_actualizar].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                    html_completo_actualizado = str(contenido_completo_soup)

                status = confluence.update_page(
                        page_id=page['id'],
                        title=title,
                        body=html_completo_actualizado,
                        version_comment="TC Grafana Prometheus"
                    )
                if status:
                    print('Página actualizada exitosamente')
                else:
                    print('Error al actualizar la página')
        
        case 'KIBANA':
            space='QAVIDEO'
            title='pruebas QA'
            page = confluence.get_page_by_title(space, title)
            html_completo_actualizado = ""
            if page:
                page2 = confluence.get_page_by_title(space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenidoSplit = contenido.split("Referencia KIBANA QA")
                soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
                table = soup.findAll('table')
                contador = 0
                cont = 0
                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')
                tablas = contenido_completo_soup.find_all('table')
                if modificar == False:

                    frase = "Referencia KIBANA QA"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None
                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if tabla_despues_de_frase:
                        indice_tabla = tablas.index(tabla_despues_de_frase)

                    indice_tabla_a_actualizar = indice_tabla
                    for index, table in enumerate(table):
                        headers = table.find_all('th')
                        header_texts = [header.get_text().strip().lower() for header in headers]
                        if "test case id".lower() in header_texts:
                            df = pd.read_html(str(table))[0]  
                            columnas_deseadas = ['Test Case ID']
                            df_seleccionado = df[columnas_deseadas]
                            for index, fila in df_seleccionado.iterrows():
                                if pd.isnull(fila['Test Case ID']) or fila['Test Case ID'] == "":
                                    fila_dict = fila.to_dict()
                                    fila_dict['Test Case ID'] = key[contador]
                                    df.at[index, 0] = fila_dict['Test Case ID']  
                                    contador = contador + 1

                            data_actualizada = df.values.tolist()
                            filas = table.find_all('tr')
                            for i, fila in enumerate(filas): 
                                celdas = fila.find_all('td')
                                for j, celda in enumerate(celdas):
                                    if j == 3:
                                        celda_valor = celda.get_text(strip=True)
                                        if pd.isnull(celda_valor) or celda_valor == "":
                                            celda.string = key[cont]
                                            cont = cont + 1
                            
                            tabla_html_actualizada = str(table)
                            if indice_tabla_a_actualizar < len(tablas):
                                tablas[indice_tabla_a_actualizar].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                            
                        indice_tabla_a_actualizar = indice_tabla_a_actualizar + 1
                    html_completo_actualizado = str(contenido_completo_soup) 

                elif modificar == True:
                    frase = "Referencia KIBANA QA"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None
                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if tabla_despues_de_frase:
                        indice_tabla = tablas.index(tabla_despues_de_frase)

                    indice_tabla_a_actualizar = indice_tabla
                    for index, table in enumerate(table):
                        headers = table.find_all('th')
                        header_texts = [header.get_text().strip().lower() for header in headers]
                        if "test case id".lower() in header_texts:
                            df = pd.read_html(str(table))[0]  
                            columnas_deseadas = ['Test Case ID']
                            df_seleccionado = df[columnas_deseadas]
                            for index, fila in df_seleccionado.iterrows():
                                fila_dict = fila.to_dict()
                                fila_dict['Test Case ID'] = key[contador]
                                df.at[index, 0] = fila_dict['Test Case ID']  
                                contador = contador + 1

                            data_actualizada = df.values.tolist()
                            filas = table.find_all('tr')
                            for i, fila in enumerate(filas): 
                                celdas = fila.find_all('td')
                                for j, celda in enumerate(celdas):
                                    if j == 3:
                                        celda.string = str(key[cont])
                                        cont = cont + 1
                            
                            tabla_html_actualizada = str(table)
                            if indice_tabla_a_actualizar < len(tablas):
                                tablas[indice_tabla_a_actualizar].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                            
                        indice_tabla_a_actualizar = indice_tabla_a_actualizar + 1
                    html_completo_actualizado = str(contenido_completo_soup) 

                status = confluence.update_page(
                                        page_id=page['id'],
                                        title=title,
                                        body=html_completo_actualizado,
                                        version_comment='TC KIBANA'
                                    )
                            
                if status:
                    print('Página actualizada exitosamente')
                else:
                    print('Error al actualizar la página')
            
                
def crearTCZabbix(project,contenido,modificar,componente,label=None,fixVersion=None):
    listaZabbix = obtenerTextoConf('ZABBIX',contenido,'Referencia ZABBIX QA',modificar)
    creaJira(project,'ZABBIX',listaZabbix,modificar,componente,label,fixVersion)

def crearTCGrafanaPlatform(project,contenido,modificar,componente,label=None,fixVersion=None):
    listaGrafanaPlatform = obtenerTextoConf('GRAFANA PLATFORM',contenido,'Referencia Grafana Plataforma QA',modificar)
    creaJira(project,'GRAFANA PLATFORM',listaGrafanaPlatform,modificar,componente,label,fixVersion)

def crearTCGrafanaPrometheus(project,contenido,modificar,componente,label=None,fixVersion=None):
    listaGraganaPrometheus = obtenerTextoConf('GRAFANA PROMETHEUS',contenido,'Referencia GRAFANA PROMETHEUS QA',modificar)
    creaJira(project,'GRAFANA PROMETHEUS',listaGraganaPrometheus,modificar,componente,label,fixVersion)

# Es necesario un número par de tablas para crear correctamente el TC
def crearTCKibana(project,contenido,modificar,componente,label=None,fixVersion=None):
    listaKibana = obtenerTextoConf('KIBANA',contenido,'Referencia KIBANA QA',modificar)
    for i in range(0,len(listaKibana),2):
        creaJira(project,'KIBANA',listaKibana[i:i+2],modificar,componente,label,fixVersion)
    modificarTesCaseId(listaIssueKibana,'KIBANA',modificar)

def main(project,monitorizacion,modificar,componente,label=None,fixVersion=None):
    space='videotools'
    title='Rebirth Catalog 01 - Loader (Openshift)'
    page = confluence.get_page_by_title(space, title)
    if page:
        
        page2 = confluence.get_page_by_title(space, title, expand='body.storage')
        contenido = page2['body']['storage']['value']

        match monitorizacion:
            case 'ZABBIX':
                crearTCZabbix(project,contenido,modificar,componente,label,fixVersion)
            case 'GRAFANA PLATFORM':
                crearTCGrafanaPlatform(project,contenido,modificar,componente,label,fixVersion)
            case 'GRAFANA PROMETHEUS':
                crearTCGrafanaPrometheus(project,contenido,modificar,componente,label,fixVersion)
            case 'KIBANA':
                crearTCKibana(project,contenido,modificar,componente,label,fixVersion)
            case 'ALL':
                crearTCZabbix(project,contenido,modificar,componente,label,fixVersion)
                crearTCGrafanaPlatform(project,contenido,modificar,componente,label,fixVersion)
                crearTCGrafanaPrometheus(project,contenido,modificar,componente,label,fixVersion)
                crearTCKibana(project,contenido,modificar,componente,label,fixVersion)
            case _:
                raise ValueError(f"Monitorizacion no reconocida: {monitorizacion}")
            
main ("MBJIRATEST","GRAFANA PLATFORM",True,"Android")
main ("MBJIRATEST","GRAFANA PROMETHEUS",False,"Android")
main ("USERSAPITC",'ZABBIX',False,"top.catalog.loader",None,"top.catalog.loader_1.0")
main ("MBJIRATEST",'KIBANA',False,"Android")