from atlassian import Confluence
import json
from bs4 import BeautifulSoup
import pandas as pd
from jira import JIRA
import copy
from dotenv import load_dotenv
import os
import argparse

class JiraIssue:
    def __init__(self, issueKey, issueType, userStoryKey, summary, labels, components, testType, testScope,
                 executionMode, automationCandidate, regression, testPriority, testReviewed, description, preRequisites,
                 dataset, procedure, expectedResult, project, fixVersion):
        self.issueKey = issueKey
        self.issueType = {'name': issueType}
        self.userStoryKey = userStoryKey
        self.summary = summary
        self.labels = convertStringToArray(labels)
        self.components = convertArrayToComponentList(
            'name', convertStringToArray(components))
        self.testType = {'value': testType}
        self.testScope = convertArrayToComponentList(
            'value', convertStringToArray(testScope))
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
        'project': jiraIssue.project,
        'issuetype': jiraIssue.issueType,
        'summary': jiraIssue.summary,
        'labels': jiraIssue.labels,
        'components': jiraIssue.components,
        'customfield_10101': jiraIssue.testType,
        'customfield_10163': jiraIssue.testScope,
        'customfield_10150': jiraIssue.executionMode,
        'customfield_10161': jiraIssue.automationCandidate,
        'customfield_10151': jiraIssue.regression,
        'customfield_10152': jiraIssue.testPriority,
        'customfield_10162': jiraIssue.testReviewed,
        'description': jiraIssue.description,
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

def getParameters() :
    parameters = {}
    space = os.getenv("Space")
    title = os.getenv("Title")
    project = os.getenv("Project")
    component = os.getenv("Componente")
    
    modificarEnv = os.getenv("Modificar")
    if modificarEnv is not None:
        modificarEnv = modificarEnv.lower() == "true"

    label = os.getenv("Label")
    fixVersion = os.getenv("FixVersion")

    labelEnv = label if label and label.lower() != "none" else None
    fixVersionEnv = fixVersion if fixVersion and fixVersion.lower() != "none" else None
    
    zabbix = os.getenv("ZABBIX", "false").lower() == "true"
    grafana_platform = os.getenv("GRAFANA PLATAFORMA", "false").lower() == "true"
    grafana_prometheus = os.getenv("GRAFANA PROMETHEUS", "false").lower() == "true"
    kibana = os.getenv("KIBANA", "false").lower() == "true"
    
    linked_ticket_zabbix = os.getenv("Zabbix Is Tested By")
    linked_ticket_graf_plat = os.getenv("Grafana Platform Is Tested By")
    linked_ticket_graf_prom = os.getenv("Grafana Prometheus Is Tested By")
    linked_ticket_kibana = os.getenv("Kibana Is Tested By")
    
    parameters = {"space" : space}
    parameters.update({"title" : title})
    parameters.update({"project" : project})
    parameters.update({"component" : component})
    parameters.update({"modify": modificarEnv})
    parameters.update({"label":labelEnv})
    parameters.update({"fixVersion":fixVersionEnv})
    parameters.update({"zabbix":zabbix})
    parameters.update({"grafana_platform":grafana_platform})
    parameters.update({"grafana_prometheus":grafana_prometheus})
    parameters.update({"kibana":kibana})
    parameters.update({"linked_ticket_zabbix":linked_ticket_zabbix})
    parameters.update({"linked_ticket_graf_plat":linked_ticket_graf_plat})
    parameters.update({"linked_ticket_graf_prom":linked_ticket_graf_prom})
    parameters.update({"linked_ticket_kibana":linked_ticket_kibana})
    
    return parameters

"""
nombre_claves_ZABBIX = {
    3: "patternToSearch",
    4: "severity",
    5: "alarmName",
    6: "alarmText",
    7: "condition",
    8: "action",
    12: "Test Case ID"
}
"""

nombre_claves_ZABBIX = {
    2: "patternToSearch",
    3: "severity",
    4: "alarmName",
    5: "alarmText",
    6: "condition",
    7: "action",
    11: "Test Case ID"
}


listaIssueKibana = []

# Obtiene información de confluence correspondiente a la monitorización
# Parametros:
# monitorizacion(str): tipo de monitorización
# contenido(str): Contenido de la página HTML
# referencia(str): Delimitador que diferencia el contenido que queremos obtener
# Retorna:
# Lista con todas la informacion obtenida


def obtenerTextoConf(monitorizacion, contenido, referencia, modificar):
    if monitorizacion == 'ZABBIX':
        listaZabbix = []
        contenidoSplit = contenido.split(referencia)
        html_completo = f"<table>{contenidoSplit[1]}</table>"
        soup = BeautifulSoup(html_completo, 'html.parser')
        table = soup.find('table')
        df = pd.read_html(str(table))[0]
        columnas_deseadas_indices = [2, 3, 4, 5, 6, 7, 11]
        max_index = df.shape[1] - 1
        if all(0 <= idx <= max_index for idx in columnas_deseadas_indices):
            columnas_deseadas_nombres = [df.columns[idx]
                                            for idx in columnas_deseadas_indices]
            df_seleccionado = df[columnas_deseadas_nombres]
            df_seleccionado.columns = columnas_deseadas_indices
        else:
            print(f"Algunos índices están fuera del rango. El rango válido es 0 a {max_index}.")

        if modificar == False:
            for index, fila in df_seleccionado.iterrows():
                fila_dict = fila.to_dict()
                if 'Recuperación' in str(fila_dict[6]):
                    condition = str(fila_dict[6]).split('Recuperación')
                    fila_dict[6] = {}
                    fila_dict[6]['alarm'] = condition[0]
                    fila_dict[6]['recovery'] = condition[1]

                nuevo_data = {
                    nombre_claves_ZABBIX[old_key]: value for old_key, value in fila_dict.items()}
                listaZabbix.append(nuevo_data)

        elif modificar == True:
            for index, fila in df_seleccionado.iterrows():
                fila_dict = fila.to_dict()
                if 'Recuperación' in str(fila_dict[6]):
                    condition = str(fila_dict[6]).split('Recuperación')
                    fila_dict[6] = {}
                    fila_dict[6]['alarm'] = condition[0]
                    fila_dict[6]['recovery'] = condition[1]

                if pd.isna(fila_dict[11]):
                    fila_dict[11] = " "

                nuevo_data = {nombre_claves_ZABBIX[old_key]: value for old_key, value in fila_dict.items(
                ) if old_key in nombre_claves_ZABBIX and not pd.isna(value)}

                if 'Test Case ID' in nombre_claves_ZABBIX and not pd.isna(fila_dict[11]):
                    nuevo_data[nombre_claves_ZABBIX[11]] = fila_dict[11]

                listaZabbix.append(nuevo_data)
        if (listaZabbix[0]['Test Case ID'] == 'Test Case ID'):
            ultimoElemento = listaZabbix.pop(0)
        return listaZabbix

    elif monitorizacion == 'GRAFANA PLATFORM':
        listaGrafana = []
        contenidoSplit = contenido.split(
            "Referencia Grafana Plataforma QA")
        soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
        table = soup.find('table')
        df = pd.read_html(str(table))[0]
        df = df.drop(df.index[0])
        columnas_deseadas = [2, 4, 5, 6, 7]
        df_seleccionado = df[columnas_deseadas]

        if modificar == False:
            for index, fila in df_seleccionado.iterrows():
                fila_dict = fila.to_dict()

                if not pd.isnull(fila_dict[2]):
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

    elif monitorizacion == 'GRAFANA PROMETHEUS':
        listaGrafana = []

        contenidoSplit = contenido.split(referencia)

        html_con_saltos = contenidoSplit[1].replace('<p>', '<p><br>')
        soup = BeautifulSoup(html_con_saltos, 'html.parser')

        tablas = soup.find_all('table')

        table = tablas[0]
        df = pd.read_html(str(table))[0]

        columnas_deseadas = [
            'Metric', 'Type', 'DB En Influx', 'Medida', 'Métrica', 'Test Case ID']
        columnas_deseadas_indices = [0, 1, 3, 6, 7, 13]

        max_index = df.shape[1] - 1
        if all(0 <= idx <= max_index for idx in columnas_deseadas_indices):
            columnas_deseadas_nombres = [df.columns[idx]
                                            for idx in columnas_deseadas_indices]
            df_seleccionado = df[columnas_deseadas_nombres]
            df_seleccionado.columns = columnas_deseadas_indices
        else:
            print(f"Algunos índices están fuera del rango. El rango válido es 0 a {max_index}.")

        df_seleccionado = df[columnas_deseadas]

        if modificar == False:
            for index, fila in df_seleccionado.iterrows():
                fila_dict = fila.to_dict()
                if pd.isnull(fila_dict['Test Case ID']):
                    if not pd.isnull(fila_dict['Métrica']):
                        fila_dict['Métrica'] = fila_dict['Métrica'].replace(
                            ' ', '\n')
                    listaGrafana.append(fila_dict)

        elif modificar:
            for index, fila in df_seleccionado.iterrows():
                fila_dict = fila.to_dict()
                # Asegurarse de que 'Métrica' es un string antes de aplicar 'replace'
                if isinstance(fila_dict['Métrica'], str):
                    fila_dict['Métrica'] = fila_dict['Métrica'].replace(' ', '\n')
                else:
                    # Convertir a string si es necesario
                    fila_dict['Métrica'] = str(fila_dict['Métrica']).replace(' ', '\n')
                listaGrafana.append(fila_dict)

        return listaGrafana

    elif monitorizacion == 'KIBANA':
        listaKibana = []
        contenidoSplit = contenido.split(referencia)
        soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
        table = soup.find_all('table')
        tablas = pd.read_html(str(table))
        if len(tablas) % 2 != 0:
            raise AssertionError(
                f"El numero de tablas es impar: {len(tablas)}")

        for i in range(0, len(tablas)):
            listaKibana.append(tablas[i].to_dict(orient='records'))
        return listaKibana


def escribirJson(nombreF, contenido):
    with open(nombreF, "w") as archivo:
        json.dump(contenido, archivo, indent=4)


def conversorJson(procedure):
    return "*GIVEN* "+procedure["GIVEN"] + "\n*WHEN* "+procedure["WHEN"]+"\n*AND* "+procedure["AND"]+"\n*THEN* "+procedure["THEN"]

# Crea el título del TC
# Parámetros:
# monitorizacion(str): tipo de monitorización
# datosFijos(diccionario): Datos obtenidos del JSON datosFijos.json
# datoConfluence(lista): Datos obtenidos de Confluence (obtenerTextoConf)


def createSummary(monitorizacion, datosFijos, datoConfluence, componente=None, functionName=None):
        if monitorizacion == 'ZABBIX':
            return f"[{datosFijos[monitorizacion]['Monitorizacion']}] " + (f"[{componente}] " if componente else "") + f"- {datoConfluence['severity']} - {datoConfluence['alarmName']}"
        elif monitorizacion == 'GRAFANA PLATFORM':
            return f"[{datosFijos[monitorizacion]['Monitorizacion']}] " + (f"[{componente}] " if componente else "") + "PLATFORM METRICS - " + datoConfluence["Metric"]
        elif monitorizacion == 'GRAFANA PROMETHEUS':
            # Extraer el nombre de la métrica antes de '{' si existe
            metric_name = datoConfluence["Metric"]
            if "{" in metric_name:
                # Obtener solo la parte antes del '{'
                metric_name = metric_name.split("{")[0]

            return f"[{datosFijos[monitorizacion]['Monitorizacion']}] " + \
                (f"[{componente}] " if componente else "") + \
                "PROMETHEUS METRICS - " + metric_name
        elif monitorizacion == 'KIBANA':
            return f"[{datosFijos[monitorizacion]['Monitorizacion']}] " + (f"[{componente}] " if componente else "") + f"- {functionName} fields mapping using index {datoConfluence[0][0]['indice']}"


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


def actualizarDatosFijos(monitorizacion, datosConf, datosFijos, componente, fn=None):

        if monitorizacion == 'ZABBIX':
            alarmName = str(datosConf.get('alarmName', ''))
            severity = str(datosConf.get('severity', ''))
            alarmText = str(datosConf.get('alarmText', ''))
            action = str(datosConf.get('action', ''))
            patternToSearch = str(datosConf.get('patternToSearch', ''))

            condition_dict = datosConf.get('condition', {})
            condition = str(condition_dict.get('alarm', '')) if isinstance(
                condition_dict, dict) else ''
            recovery = str(condition_dict.get('recovery', '')
                           ) if isinstance(condition_dict, dict) else ''

            datosFijos[monitorizacion]['Procedure']['AND'] = datosFijos[monitorizacion]['Procedure']['AND'].replace(
                'ALARMNAME', alarmName)
            datosFijos[monitorizacion]['Procedure']['AND'] = datosFijos[monitorizacion]['Procedure']['AND'].replace(
                'COMPONENTNAME', componente)

            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                'SEVERITY', severity)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                'ALARMNAME', alarmName)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                'ALARMTEXT', alarmText)  # Convertido a cadena
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                'ACTION', action)

            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'PATTERNTOSEARCH', patternToSearch)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'CONDITION', condition)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'RECOVERY', recovery)

            dbInflux = str(datosConf.get('DB En Influx', ''))
            medida = str(datosConf.get('Medida', ''))
            metrica = str(datosConf.get('Métrica', ''))
            type = str(datosConf.get('Type', ''))

            datosFijos[monitorizacion]['PreRequisites'] = datosFijos[monitorizacion]['PreRequisites'].replace(
                'DBINFLUX', dbInflux)

            if medida:
                datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                    'MEDIDA', medida)

            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'METRIC', componente)

            if metrica:
                datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                    'M\u00e9trica', metrica)

            if type:
                datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                    'TYPE', type)

            datosFijos[monitorizacion]['Procedure'] = conversorJson(
                datosFijos[monitorizacion]['Procedure'])

            return datosFijos

        elif monitorizacion == 'KIBANA':
            # Convertir 'fn' a cadena, utilizando una cadena vacía si 'fn' es None o no es str
            functionName = str(fn) if fn is not None else ""

            cont = "\n|"

            # Generar el encabezado de forma segura, manejando valores vacíos
            encabezado = "||*" + "*||*".join([
                # Convertir a cadena solo si v no es None
                str(v) if v is not None else ""
                for k, v in datosConf[1][0].items()
                # Encabezado vacío si datosConf[1] está vacío
            ]) + "*||" if datosConf[1] else "||"

            # Reemplazos en ExpectedResult con valores predeterminados
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                "TITULOS", encabezado)
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                "FUNCTIONNAME", functionName)

            # Generar el contenido con valores vacíos por defecto cuando sea necesario
            for i in datosConf[1]:
                cont += "\n|"
                for key in i.keys():
                    # Valor vacío si es None
                    value = str(i[key]) if i[key] is not None else ""
                    cont += value + "|"

            # Reemplazar 'CONTENT' en ExpectedResult solo si 'cont' tiene contenido
            datosFijos[monitorizacion]['ExpectedResult'] = datosFijos[monitorizacion]['ExpectedResult'].replace(
                "CONTENT", cont)

            return datosFijos

        elif monitorizacion == 'GRAFANA PLATFORM':
            # Obtener valores de 'datosConf', usando una cadena vacía por defecto si algún valor no está presente
            # Valor por defecto vacío si falta o es None
            dbInflux = str(datosConf.get('DB en Influx', ''))
            # Valor por defecto vacío si falta o es None
            medida = str(datosConf.get('Medida', ''))
            # Valor por defecto vacío si falta o es None
            metrica = str(datosConf.get('Metrica', ''))

            # Reemplazos en 'PreRequisites' y 'DataSet'
            datosFijos[monitorizacion]['PreRequisites'] = datosFijos[monitorizacion]['PreRequisites'].replace(
                'DBINFLUX', dbInflux)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'MEDIDA', medida)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'POD', componente)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'METRICA', metrica)

            return datosFijos

        elif monitorizacion == 'GRAFANA PROMETHEUS':
            dbInflux = datosConf.get('DB En Influx', '')
            medida = datosConf.get('Medida', '')
            metrica = datosConf.get('Métrica', '')
            type = datosConf.get('Type', '')

            # Asegurarse de que los valores numéricos se convierten a cadena antes de hacer replace
            # Convertir a str si existe, sino dejar vacío
            medida = str(medida) if medida else ''
            # Convertir a str si existe
            metrica = str(metrica) if metrica else ''
            type = str(type) if type else ''  # Convertir a str si existe

            # Reemplazar 'DBINFLUX' en 'PreRequisites'
            datosFijos[monitorizacion]['PreRequisites'] = datosFijos[monitorizacion]['PreRequisites'].replace(
                'DBINFLUX', dbInflux)

            # Reemplazar 'MEDIDA' solo si el valor 'medida' está presente
            if medida:
                datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                    'MEDIDA', medida)

            # Reemplazar 'METRIC' con 'componentName'
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'METRIC', componente)

            # Reemplazar 'Métrica' solo si 'metrica' está presente
            if metrica:
                datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                    'M\u00e9trica', metrica)

            # Reemplazar 'TYPE' solo si 'type' está presente
            if type:
                datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                    'TYPE', type)

            return datosFijos


def buscar_ticket_existente(jira, busqueda, criterio_busqueda):
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

def creaJira(jenkinsParameters, monitorizacion, datosConfluence):
    options = {'server': 'https://jira.tid.es/'}
    userJira = 'qasupport'
    passJIRA = 'temporal'
    jira = jiraConnection(options, userJira, passJIRA)

    linked_ticket_zabbix = jenkinsParameters["linked_ticket_zabbix"]
    linked_ticket_graf_plat = jenkinsParameters["linked_ticket_graf_plat"]
    linked_ticket_graf_prom = jenkinsParameters["linked_ticket_graf_prom"]
    linked_ticket_kibana = jenkinsParameters["linked_ticket_kibana"]

    if monitorizacion == 'ZABBIX':
        print ("\n** ZABBIX **\n\n")
        listaIssueZabbix = []
        for dato in datosConfluence:
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, dato, datosFijos, jenkinsParameters["component"])

            if jenkinsParameters["fixVersion"] is not None:
                fixVersionSplit = jenkinsParameters["fixVersion"].split(",")
                fixVersionFinal = []
                for fv in fixVersionSplit:
                    temporal = {'name': fv}
                    fixVersionFinal.append(temporal)
            else:
                fixVersionFinal = None

            jiraIssue = JiraIssue("", "Test Case", "", createSummary(monitorizacion, datosFijos, dato, jenkinsParameters["component"]), jenkinsParameters["label"], jenkinsParameters["component"], datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'], datosFijos[monitorizacion][
                                        'ExecutionMode'], datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'], datosFijos[monitorizacion][
                                        'TestPriority'], datosFijos[monitorizacion]['TestReviewed'],
                                    "", datosFijos[monitorizacion]['PreRequisites'], datosFijos[monitorizacion]['DataSet'],
                                    datosFijos[monitorizacion]['Procedure'], datosFijos[monitorizacion]['ExpectedResult'], jenkinsParameters["project"], fixVersionFinal)
            
            if jenkinsParameters["modify"] == True:
                key = dato['Test Case ID']
                ticket_existente = buscar_ticket_existente_por_key(
                    jira, key)
                if ticket_existente:
                    fields_to_update = createIssueDict(jiraIssue)
                    fields_to_update.pop('key', None)
                    ticket_existente.update(fields=fields_to_update)
                    print(f'Ticket {ticket_existente.key} actualizado.')
                    print(jiraIssue.summary)
                    print(jiraIssue.issueKey)
                    issue = jira.create_issue(fields=createIssueDict(jiraIssue))  # Crea el issue correctamente
                    listaIssueZabbix.append(ticket_existente)
                    if linked_ticket_zabbix:
                        try:
                            # Verifica que linked_ticket_zabbix tenga el formato adecuado (ID del ticket)
                            linked_ticket = jira.issue(linked_ticket_zabbix)  # Obtener el ticket relacionado
                            print(f"Enlazando ticket {issue.key} con {linked_ticket.key}.")

                            # Crea el enlace entre los tickets
                            jira.create_issue_link('tests', issue.key, linked_ticket.key)
                            print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")

                        except Exception as e:
                            print(f"Error al intentar enlazar los tickets: {e}")
                else:
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    print(f'Ticket {jiraIssue.issueKey} creado.')
                    print(jiraIssue.summary)
                    print(jiraIssue.issueKey)
                    issue = jira.create_issue(fields=createIssueDict(jiraIssue))  # Crea el issue correctamente
                    listaIssueZabbix.append(str(jiraIssue.issueKey))
                    if linked_ticket_zabbix:
                        linked_ticket = jira.issue(linked_ticket_zabbix)  # Obtenemos el ticket relacionado
                        # Usa .key para obtener el key del ticket
                        jira.create_issue_link('tests', issue.key, linked_ticket.key)
                        print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")

            elif jenkinsParameters["modify"] == False:
                if 'Test Case ID' in dato:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(
                        jira, key)
                    if ticket_existente:
                        print("TC EXISTENTE: "+str(key))
                        if linked_ticket_zabbix:
                            try:
                                linked_ticket = jira.issue(linked_ticket_zabbix)  # Obtener el ticket relacionado
                                print(f"Enlazando ticket {ticket_existente.key} con {linked_ticket.key}.")

                                jira.create_issue_link('tests', ticket_existente.key, linked_ticket.key)
                                print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket.key}\n")

                            except Exception as e:
                                print(f"Error al intentar enlazar los tickets: {e}")
                    else:
                        print(jiraIssue.summary)
                        # Solo creamos el ticket una vez
                        issue = jira.create_issue(fields=createIssueDict(jiraIssue))  # Crea el issue correctamente
                        listaIssueZabbix.append(str(issue.key))  # Usamos issue.key aquí
                        print(f'Ticket {issue.key} creado.')

                        if linked_ticket_zabbix:
                            try:
                                # Verifica que linked_ticket_zabbix tenga el formato adecuado (ID del ticket)
                                linked_ticket = jira.issue(linked_ticket_zabbix)  # Obtener el ticket relacionado
                                print(f"Enlazando ticket {issue.key} con {linked_ticket.key}.")

                                # Crea el enlace entre los tickets
                                jira.create_issue_link('tests', issue.key, linked_ticket.key)
                                print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")

                            except Exception as e:
                                print(f"Error al intentar enlazar los tickets: {e}")

        modificarTesCaseId(listaIssueZabbix, 'ZABBIX', jenkinsParameters["modify"])

    elif monitorizacion == 'GRAFANA PLATFORM':
        print("\n** GRAFANA PLATAFORMA **\n\n")
        listaIssueGrafanaPlatform = []
        for dato in datosConfluence:
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, dato, datosFijos, jenkinsParameters["component"])

            if jenkinsParameters["fixVersion"] is not None:
                fixVersionSplit = jenkinsParameters["fixVersion"].split(",")
                fixVersionFinal = [{'name': fv} for fv in fixVersionSplit]
            else:
                fixVersionFinal = None

            jiraIssue = JiraIssue(
                "",
                "Test Case",
                "",
                createSummary(monitorizacion, datosFijos, dato, jenkinsParameters["component"]),
                jenkinsParameters["label"],
                jenkinsParameters["component"],
                datosFijos[monitorizacion]['TestType'],
                datosFijos[monitorizacion]['TestScope'],
                datosFijos[monitorizacion]['ExecutionMode'],
                datosFijos[monitorizacion]['AutomationCandidate'],
                datosFijos[monitorizacion]['Regression'],
                datosFijos[monitorizacion]['TestPriority'],
                datosFijos[monitorizacion]['TestReviewed'],
                datosFijos[monitorizacion]['Description'],
                datosFijos[monitorizacion]['PreRequisites'],
                datosFijos[monitorizacion]['DataSet'],
                "",
                "",
                jenkinsParameters["project"],
                fixVersionFinal
            )

            key = dato['Test Case ID']
            ticket_existente = buscar_ticket_existente_por_key(jira, key)

            if jenkinsParameters["modify"] == True:
                if ticket_existente:
                    # Actualizar ticket existente
                    fields_to_update = createIssueDict(jiraIssue)
                    fields_to_update.pop('key', None)
                    ticket_existente.update(fields=fields_to_update)
                    print(f'Ticket {ticket_existente.key} actualizado.')
                    listaIssueGrafanaPlatform.append(ticket_existente.key)

                    # Enlazar si es necesario
                    if linked_ticket_graf_plat:
                        linked_ticket = jira.issue(linked_ticket_graf_plat)  # Obtenemos el ticket relacionado
                        jira.create_issue_link('tests', ticket_existente.key, linked_ticket.key)
                        print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket.key}\n")
                else:
                    # Crear y enlazar un nuevo ticket si no existe
                    issue = jira.create_issue(fields=createIssueDict(jiraIssue))
                    print(jiraIssue.summary)
                    print(f'Ticket {issue.key} creado.')
                    listaIssueGrafanaPlatform.append(issue.key)

                    if linked_ticket_graf_plat:
                        linked_ticket = jira.issue(linked_ticket_graf_plat)
                        jira.create_issue_link('tests', issue.key, linked_ticket.key)
                        print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")

            elif jenkinsParameters["modify"] == False:
                if ticket_existente:
                    print("TC EXISTENTE: " + str(key))
                else:
                    # Crear y enlazar un nuevo ticket solo si no existe
                    issue = jira.create_issue(fields=createIssueDict(jiraIssue))
                    print(jiraIssue.summary)
                    print(f'Ticket {issue.key} creado.')
                    listaIssueGrafanaPlatform.append(issue.key)

                    if linked_ticket_graf_plat:
                        linked_ticket = jira.issue(linked_ticket_graf_plat)
                        jira.create_issue_link('tests', issue.key, linked_ticket.key)
                        print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")

        modificarTesCaseId(listaIssueGrafanaPlatform,
                            'GRAFANA PLATFORM', jenkinsParameters["modify"])

    elif monitorizacion == 'GRAFANA PROMETHEUS':
        print("\n** GRAFANA PROMETHEUS **\n\n")
        listaIssueGrafanaPrometheus = []
        metrics_dict = {}
        created_tickets = set()

        for dato in datosConfluence:
            if "{" in dato["Metric"]:
                metric_name = dato["Metric"].split("{")[0]
                metric_params = dato["Metric"].split("{", 1)[1].strip("}")
            else:
                metric_name = dato["Metric"]
                metric_params = None

            if metric_name not in metrics_dict:
                metrics_dict[metric_name] = []

            if metric_params:
                metrics_dict[metric_name].append(f"{{{metric_params}}}")

        for metric_name, params in metrics_dict.items():
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, {"Metric": metric_name}, datosFijos, jenkinsParameters["component"]
            )
            dataset_content = datosFijos[monitorizacion]['DataSet']

            new_table = "\n\n\n|| Metric ||\n"
            for param in params:
                new_table += f"| {param} |\n"

            dataset_content += "\n" + new_table

            if jenkinsParameters["fixVersion"] is not None:
                fixVersionSplit = jenkinsParameters["fixVersion"].split(",")
                fixVersionFinal = [{'name': fv} for fv in fixVersionSplit]
            else:
                fixVersionFinal = None

            jiraIssue = JiraIssue(
                "", "Test Case", "",
                createSummary(monitorizacion, datosFijos, {
                    "Metric": metric_name}, jenkinsParameters["component"]),
                jenkinsParameters["label"], jenkinsParameters["component"],
                datosFijos[monitorizacion]['TestType'],
                datosFijos[monitorizacion]['TestScope'],
                datosFijos[monitorizacion]['ExecutionMode'],
                datosFijos[monitorizacion]['AutomationCandidate'],
                datosFijos[monitorizacion]['Regression'],
                datosFijos[monitorizacion]['TestPriority'],
                datosFijos[monitorizacion]['TestReviewed'],
                datosFijos[monitorizacion]['Description'],
                datosFijos[monitorizacion]['PreRequisites'],
                dataset_content,
                "", "", jenkinsParameters["project"], fixVersionFinal
            )

            if metric_name not in created_tickets:
                key = dato['Test Case ID']
                ticket_existente = buscar_ticket_existente_por_key(jira, key)

                if ticket_existente:
                    # Actualizar ticket existente si está en modo "modify"
                    if jenkinsParameters["modify"]:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(f'Ticket {ticket_existente.key} actualizado.')
                        listaIssueGrafanaPrometheus.append(ticket_existente.key)

                    # Enlazar ticket existente con el relacionado
                    if linked_ticket_graf_prom:
                        linked_ticket = jira.issue(linked_ticket_graf_prom)
                        jira.create_issue_link('tests', ticket_existente.key, linked_ticket.key)
                        print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket.key}\n")

                else:
                    # Crear un nuevo ticket si no existe
                    issue = jira.create_issue(fields=createIssueDict(jiraIssue))
                    created_tickets.add(metric_name)
                    print(jiraIssue.summary)
                    print(f'Ticket {issue.key} creado.')
                    listaIssueGrafanaPrometheus.append(issue.key)

                    # Enlazar ticket recién creado con el relacionado
                    if linked_ticket_graf_prom:
                        linked_ticket = jira.issue(linked_ticket_graf_prom)
                        jira.create_issue_link('tests', issue.key, linked_ticket.key)
                        print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")

            else:
                print(f"El ticket para la métrica {metric_name} ya fue creado previamente.")

        modificarTesCaseId(listaIssueGrafanaPrometheus, 'GRAFANA PROMETHEUS', jenkinsParameters["modify"])


    elif monitorizacion == 'KIBANA':
        if jenkinsParameters["fixVersion"] is not None:
            fixVersionSplit = jenkinsParameters["fixVersion"].split(",")
            fixVersionFinal = [{'name': fv} for fv in fixVersionSplit]
        else:
            fixVersionFinal = None

        created_tickets = set()

        if len(datosConfluence[0]) > 1:
            for dato in datosConfluence[0]:
                datosFijos = cargarJson('datosFijos.json')
                datosFijos = actualizarDatosFijos(
                    monitorizacion, datosConfluence, datosFijos, jenkinsParameters["component"], dato['functionName']
                )

                jiraIssue = JiraIssue(
                    "", "Test Case", "",
                    createSummary(monitorizacion, datosFijos, datosConfluence, jenkinsParameters["component"], dato['functionName']),
                    jenkinsParameters["label"], jenkinsParameters["component"],
                    datosFijos[monitorizacion]['TestType'],
                    datosFijos[monitorizacion]['TestScope'],
                    datosFijos[monitorizacion]['ExecutionMode'],
                    datosFijos[monitorizacion]['AutomationCandidate'],
                    datosFijos[monitorizacion]['Regression'],
                    datosFijos[monitorizacion]['TestPriority'],
                    datosFijos[monitorizacion]['TestReviewed'],
                    "", "", datosFijos[monitorizacion]['DataSet'],
                    "", datosFijos[monitorizacion]['ExpectedResult'], jenkinsParameters["project"], fixVersionFinal
                )

                key = dato['Test Case ID']
                if key not in created_tickets:
                    ticket_existente = buscar_ticket_existente_por_key(jira, key)
                    if ticket_existente:
                        if jenkinsParameters["modify"]:
                            fields_to_update = createIssueDict(jiraIssue)
                            fields_to_update.pop('key', None)
                            ticket_existente.update(fields=fields_to_update)
                            print(f'Ticket {ticket_existente.key} actualizado.')
                            listaIssueKibana.append(ticket_existente.key)

                        if linked_ticket_kibana:
                            linked_ticket = jira.issue(linked_ticket_kibana)
                            jira.create_issue_link('tests', ticket_existente.key, linked_ticket.key)
                            print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket.key}\n")
                    else:
                        issue = jira.create_issue(fields=createIssueDict(jiraIssue))
                        created_tickets.add(key)
                        print(jiraIssue.summary)
                        print(f'Ticket {issue.key} creado.')
                        listaIssueKibana.append(issue.key)

                        if linked_ticket_kibana:
                            linked_ticket = jira.issue(linked_ticket_kibana)
                            jira.create_issue_link('tests', issue.key, linked_ticket.key)
                            print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")
                else:
                    print(f"El ticket con Test Case ID {key} ya fue procesado previamente.")

        else:
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, datosConfluence, datosFijos, jenkinsParameters["component"], datosConfluence[0][0]['functionName']
            )

            jiraIssue = JiraIssue(
                "", "Test Case", "",
                createSummary(monitorizacion, datosFijos, datosConfluence, jenkinsParameters["component"], datosConfluence[0][0]['functionName']),
                jenkinsParameters["label"], jenkinsParameters["component"],
                datosFijos[monitorizacion]['TestType'],
                datosFijos[monitorizacion]['TestScope'],
                datosFijos[monitorizacion]['ExecutionMode'],
                datosFijos[monitorizacion]['AutomationCandidate'],
                datosFijos[monitorizacion]['Regression'],
                datosFijos[monitorizacion]['TestPriority'],
                datosFijos[monitorizacion]['TestReviewed'],
                "", "", datosFijos[monitorizacion]['DataSet'],
                "", datosFijos[monitorizacion]['ExpectedResult'], jenkinsParameters["project"], fixVersionFinal
            )

            key = datosConfluence[0][0]['Test Case ID']
            if key not in created_tickets:
                ticket_existente = buscar_ticket_existente_por_key(jira, key)
                if ticket_existente:
                    if jenkinsParameters["modify"]:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(f'Ticket {ticket_existente.key} actualizado.')
                        listaIssueKibana.append(ticket_existente.key)

                    if linked_ticket_kibana:
                        linked_ticket = jira.issue(linked_ticket_kibana)
                        jira.create_issue_link('tests', ticket_existente.key, linked_ticket.key)
                        print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket.key}\n")
                else:
                    issue = jira.create_issue(fields=createIssueDict(jiraIssue))
                    created_tickets.add(key)
                    print(jiraIssue.summary)
                    print(f'Ticket {issue.key} creado.')
                    listaIssueKibana.append(issue.key)

                    if linked_ticket_kibana:
                        linked_ticket = jira.issue(linked_ticket_kibana)
                        jira.create_issue_link('tests', issue.key, linked_ticket.key)
                        print(f"Ticket {issue.key} enlazado con {linked_ticket.key}\n")
            else:
                print(f"El ticket con Test Case ID {key} ya fue procesado previamente.")



def crearJson(diccionario, archivo):
    with open(archivo, 'w') as file:
        json.dump(diccionario, file, indent=4)


def obtenerTable(space, title, referencia):
    page2 = confluence.get_page_by_title(space, title, expand='body.storage')
    contenido = page2['body']['storage']['value']
    contenidoSplit = contenido.split(referencia)
    soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
    table = soup.find('table')
    return table


def actualizarConfluence(titulo, page, htmlActualizado, comentario):
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


def modificarTesCaseId(key, monitorizacion, modificar):
        space = jenkinsParameters["space"]
        title = jenkinsParameters["title"]
        if monitorizacion == 'ZABBIX':      
            page = confluence.get_page_by_title(space, title)

            if page:
                page2 = confluence.get_page_by_title(
                    space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenido_completo_soup = BeautifulSoup(
                    contenido, 'html.parser')
                tablas = contenido_completo_soup.find_all('table')

                if modificar == False:
                    frase = "3.2.3 PARSEO DE ARCHIVOS DE LOG"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None

                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if not tabla_despues_de_frase:
                        print("No se encontró la tabla después de la frase.")
                        return

                    indice_tabla_a_actualizar = tablas.index(
                        tabla_despues_de_frase)

                    tabla_original = tablas[indice_tabla_a_actualizar]
                    primer_tr_original = tabla_original.find('tr')
                    primer_tr_copy = copy.deepcopy(primer_tr_original)

                    first_tr = tabla_original.find('tr')
                    if first_tr:
                        first_tr.decompose()

                    df = pd.read_html(str(tabla_original))[0]
                    # Aseguramos que estamos manipulando la columna correcta
                    columnas_deseadas = [11]
                    df_seleccionado = df[columnas_deseadas]

                    contador = 0
                    for index, fila in df.iterrows():
                        # Asignamos el valor de key[contador] a la columna 11 (Test Case ID)
                        # Comprobamos que no excedemos el tamaño de key
                        if contador < len(key):
                            df.at[index, 11] = key[contador]
                            contador += 1
                        if contador == len(key):
                            break

                    data_actualizada = df.values.tolist()
                    filas = tabla_original.find_all('tr')

                    # Ahora procesamos las filas de la tabla original y asignamos el TC correspondiente en cada fila
                    contador = 0  # Reseteamos el contador aquí para que se asigne correctamente el TC a cada fila
                    # Empezamos desde la segunda fila
                    for i, fila in enumerate(filas[1:], start=1):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 11:
                                # Solo modificamos la columna 11 (Test Case ID)
                                if contador < len(key):
                                    # Crear un enlace HTML con el valor de la clave
                                    enlace = f'<a href="https://jira.tid.es/browse/{key[contador]}">{key[contador]}</a>'
                                    celda.string = ''  # Limpiar el contenido de la celda
                                    # Insertar el enlace
                                    celda.append(BeautifulSoup(enlace, 'html.parser'))
                                    contador += 1

                    tabla_html_actualizada = str(tabla_original)
                    tabla_html_actualizada = BeautifulSoup(
                        tabla_html_actualizada, 'html.parser')
                    tabla_original.clear()
                    tabla_original.append(primer_tr_copy)
                    for fila in tabla_html_actualizada.find_all('tr'):
                        tabla_original.append(fila)

                    tablas[indice_tabla_a_actualizar].replace_with(
                        tabla_original)

                    html_completo_actualizado = str(contenido_completo_soup)

                elif modificar == True:
                    frase = "3.2.3 PARSEO DE ARCHIVOS DE LOG REDIS PARA MONITORIZACIÓN"
                    frase_tag = contenido_completo_soup.find(string=frase)
                    tabla_despues_de_frase = None

                    if frase_tag:
                        siguiente_elemento = frase_tag.find_next()
                        while siguiente_elemento:
                            if siguiente_elemento.name == 'table':
                                tabla_despues_de_frase = siguiente_elemento
                                break
                            siguiente_elemento = siguiente_elemento.find_next()

                    if not tabla_despues_de_frase:
                        print("No se encontró la tabla después de la frase.")
                        return

                    indice_tabla_a_actualizar = tablas.index(
                        tabla_despues_de_frase)

                    tabla_original = tablas[indice_tabla_a_actualizar]
                    primer_tr_original = tabla_original.find('tr')
                    primer_tr_copy = copy.deepcopy(primer_tr_original)

                    first_tr = tabla_original.find('tr')
                    if first_tr:
                        first_tr.decompose()

                    df = pd.read_html(str(tabla_original))[0]
                    # Aseguramos que estamos manipulando la columna correcta
                    columnas_deseadas = [11]
                    df_seleccionado = df[columnas_deseadas]

                    contador = 0
                    for index, fila in df.iterrows():
                        # Asignamos el valor de key[contador] a la columna 11 (Test Case ID)
                        # Comprobamos que no excedemos el tamaño de key
                        if contador < len(key):
                            df.at[index, 11] = key[contador]
                            contador += 1
                        if contador == len(key):
                            break

                    data_actualizada = df.values.tolist()
                    filas = tabla_original.find_all('tr')

                    # Ahora procesamos las filas de la tabla original y asignamos el TC correspondiente en cada fila
                    contador = 0  # Reseteamos el contador aquí para que se asigne correctamente el TC a cada fila
                    # Empezamos desde la segunda fila
                    for i, fila in enumerate(filas[1:], start=1):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 11:
                                # Solo modificamos la columna 11 (Test Case ID)
                                if contador < len(key):
                                    # Crear un enlace HTML con el valor de la clave
                                    enlace = f'<a href="https://jira.tid.es/browse/{key[contador]}">{key[contador]}</a>'
                                    celda.string = ''  # Limpiar el contenido de la celda
                                    # Insertar el enlace
                                    celda.append(BeautifulSoup(
                                        enlace, 'html.parser'))
                                    contador += 1

                    tabla_html_actualizada = str(tabla_original)
                    tabla_html_actualizada = BeautifulSoup(
                        tabla_html_actualizada, 'html.parser')
                    tabla_original.clear()
                    tabla_original.append(primer_tr_copy)
                    for fila in tabla_html_actualizada.find_all('tr'):
                        tabla_original.append(fila)

                    tablas[indice_tabla_a_actualizar].replace_with(
                        tabla_original)

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

        elif monitorizacion == 'GRAFANA PLATFORM':
            page = confluence.get_page_by_title(space, title)
            if page:
                page2 = confluence.get_page_by_title(
                    space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenidoSplit = contenido.replace("&nbsp;", "").split(
                    "Referencia Grafana Plataforma QA")
                soup = BeautifulSoup(contenidoSplit[1], 'html.parser')
                table = soup.find('table')
                df = pd.read_html(str(table))[0]
                df = df.drop(df.index[0])
                columnas_deseadas = [2, 4, 5, 6, 7]
                df_seleccionado = df[columnas_deseadas]
                contenido_completo_soup = BeautifulSoup(
                    contenido, 'html.parser')
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
                                if data_actualizada[i-1][j] in key:
                                    nuevo_contenido = f'<a href="https://jira.tid.es/browse/{data_actualizada[i-1][j]}">{data_actualizada[i-1][j]}</a>'
                                else:
                                    nuevo_contenido = f'<strong>{data_actualizada[i-1][j]}</strong>'
                                celda.string = ''
                                celda.append(BeautifulSoup(
                                    nuevo_contenido, 'html.parser'))

                    tabla_html_actualizada = str(table)
                    tabla_html_actualizada = tabla_html_actualizada.replace(
                        'nan', 'N/A')

                    if indice_tabla_a_actualizar < len(tablas):
                        tablas[indice_tabla_a_actualizar].replace_with(
                            BeautifulSoup(tabla_html_actualizada, 'html.parser'))

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
                                if data_actualizada[i-1][j] in key:
                                    nuevo_contenido = f'<a href="https://jira.tid.es/browse/{data_actualizada[i-1][j]}">{data_actualizada[i-1][j]}</a>'
                                else:
                                    nuevo_contenido = f'<strong>{data_actualizada[i-1][j]}</strong>'
                                celda.string = ''
                                celda.append(BeautifulSoup(nuevo_contenido, 'html.parser'))

                    tabla_html_actualizada = str(table)
                    tabla_html_actualizada = tabla_html_actualizada.replace('nan', 'N/A')

                    if indice_tabla_a_actualizar < len(tablas):
                        tablas[indice_tabla_a_actualizar].replace_with(
                            BeautifulSoup(tabla_html_actualizada, 'html.parser'))

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

        elif monitorizacion == 'GRAFANA PROMETHEUS':
            page = confluence.get_page_by_title(space, title)
            if page:
                page2 = confluence.get_page_by_title(space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']
                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')
                contenidoSplit = contenido.split("Referencia GRAFANA PROMETHEUS QA")
                if len(contenidoSplit) < 2:
                    print("No se encontró la referencia 'Referencia GRAFANA PROMETHEUS QA'.")
                    return

                contenido_despues_referencia = contenidoSplit[1]
                contenido_despues_soup = BeautifulSoup(contenido_despues_referencia, 'html.parser')

                tablas = contenido_despues_soup.find_all('table')
                tabla_despues_de_frase = tablas[0]
                df = pd.read_html(str(tabla_despues_de_frase))[0]
                df = df.drop(df.index[0])
                columnas_deseadas_indices = [0, 1, 3, 6, 7, 13]

                max_index = df.shape[1] - 1
                if all(0 <= idx <= max_index for idx in columnas_deseadas_indices):
                    columnas_deseadas_nombres = [df.columns[idx] for idx in columnas_deseadas_indices]
                    df_seleccionado = df[columnas_deseadas_nombres]
                    df_seleccionado.columns = columnas_deseadas_indices
                else:
                    print(f"Algunos índices están fuera del rango. El rango válido es 0 a {max_index}.")
                    return

                if not modificar:
                    contador = 0
                    for index, fila in df_seleccionado.iterrows():
                        fila_dict = fila.to_dict()
                        # Verificamos si la columna 13 está vacía (Test Case ID)
                        if pd.isnull(fila_dict[13]) or fila_dict[13] == "":
                            if contador == len(key):
                                break
                            fila_dict[13] = key[contador]
                            df.at[index, 13] = fila_dict[13]
                            contador += 1

                    filas = tabla_despues_de_frase.find_all('tr')
                    cont = 0
                    valorMetricAux = ""
                    for i, fila in enumerate(filas):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 0:
                                celda_valor_aux = celda.get_text(strip=True)
                                valorMetric = celda_valor_aux.split("{")[0]
                                if not valorMetricAux:
                                    valorMetricAux = valorMetric

                            if j == 13:  # Columna Test Case ID
                                celda_valor = celda.get_text(strip=True)
                                if pd.isnull(celda_valor) or celda_valor == "":
                                    if valorMetric != valorMetricAux:
                                        cont += 1
                                        valorMetricAux = valorMetric
                                    if cont < len(key):
                                        enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                        celda.string = ''  # Limpiar el contenido de la celda
                                        celda.append(BeautifulSoup(enlace, 'html.parser'))

                    filas_actualizadas = []
                    for fila in filas:
                        celdas = fila.find_all('td')
                        if len(celdas) > 13:
                            if pd.isnull(celdas[13].get_text(strip=True)) or celdas[13].get_text(strip=True) == "":
                                if cont < len(key):
                                    enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                    celdas[13].string = ''
                                    celdas[13].append(BeautifulSoup(enlace, 'html.parser'))
                                    cont += 1
                        filas_actualizadas.append(fila)

                    celdas_fila_13 = []
                    for fila in filas_actualizadas:
                        celdas = fila.find_all('td')
                        if len(celdas) > 13:
                            celdas_fila_13.append(celdas[13])

                    i = 0
                    while i < len(celdas_fila_13):
                        valor_celda = celdas_fila_13[i].get_text(strip=True)
                        j = i + 1
                        while j < len(celdas_fila_13) and celdas_fila_13[j].get_text(strip=True) == valor_celda:
                            celdas_fila_13[j].extract()
                            j += 1
                        if j > i + 1:
                            celdas_fila_13[i]['rowspan'] = j - i
                        i = j

                    tabla_html_actualizada = str(tabla_despues_de_frase)
                    tablas[0].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                elif modificar:
                    contador = 0
                    for index, fila in df_seleccionado.iterrows():
                        fila_dict = fila.to_dict()
                        # Verificamos si la columna 13 está vacía (Test Case ID)
                        if pd.isnull(fila_dict[13]) or fila_dict[13] == "":
                            if contador == len(key):
                                break
                            fila_dict[13] = key[contador]
                            df.at[index, 13] = fila_dict[13]
                            contador += 1

                    filas = tabla_despues_de_frase.find_all('tr')
                    cont = 0
                    valorMetricAux = ""
                    for i, fila in enumerate(filas):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 0:
                                celda_valor_aux = celda.get_text(strip=True)
                                valorMetric = celda_valor_aux.split("{")[0]
                                if not valorMetricAux:
                                    valorMetricAux = valorMetric

                            if j == 13:  # Columna Test Case ID
                                celda_valor = celda.get_text(strip=True)
                                if pd.isnull(celda_valor) or celda_valor == "":
                                    if valorMetric != valorMetricAux:
                                        cont += 1
                                        valorMetricAux = valorMetric
                                    if cont < len(key):
                                        enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                        celda.string = ''  # Limpiar el contenido de la celda
                                        celda.append(BeautifulSoup(enlace, 'html.parser'))

                    filas_actualizadas = []
                    for fila in filas:
                        celdas = fila.find_all('td')
                        if len(celdas) > 13:
                            if pd.isnull(celdas[13].get_text(strip=True)) or celdas[13].get_text(strip=True) == "":
                                if cont < len(key):
                                    enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                    celdas[13].string = ''
                                    celdas[13].append(BeautifulSoup(enlace, 'html.parser'))
                                    cont += 1
                        filas_actualizadas.append(fila)

                    celdas_fila_13 = []
                    for fila in filas_actualizadas:
                        celdas = fila.find_all('td')
                        if len(celdas) > 13:
                            celdas_fila_13.append(celdas[13])

                    i = 0
                    while i < len(celdas_fila_13):
                        valor_celda = celdas_fila_13[i].get_text(strip=True)
                        j = i + 1
                        while j < len(celdas_fila_13) and celdas_fila_13[j].get_text(strip=True) == valor_celda:
                            celdas_fila_13[j].extract()
                            j += 1
                        if j > i + 1:
                            celdas_fila_13[i]['rowspan'] = j - i
                        i = j

                    tabla_html_actualizada = str(tabla_despues_de_frase)
                    tablas[0].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')

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
                    tabla_despues_de_frase.replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                else:
                    print("Error: No se encontró una tabla después de la referencia.")
                    return

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


        elif monitorizacion == 'KIBANA':
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

                if not modificar:  # Si modificar es False
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
                        header_texts = [header.get_text().strip().lower()
                                        for header in headers]
                        if "test case id".lower() in header_texts:
                            df = pd.read_html(str(table))[0]
                            columnas_deseadas = ['Test Case ID']
                            df_seleccionado = df[columnas_deseadas]
                            for index, fila in df_seleccionado.iterrows():
                                if pd.isnull(fila['Test Case ID']) or fila['Test Case ID'] == "":
                                    fila_dict = fila.to_dict()
                                    # Ahora, en lugar de solo poner el Test Case ID, ponemos un enlace a Jira
                                    fila_dict['Test Case ID'] = f'<a href="https://jira.tid.es/browse/{key[contador]}">{key[contador]}</a>'
                                    df.at[index, 0] = fila_dict['Test Case ID']
                                    contador = contador + 1

                            data_actualizada = df.values.tolist()
                            filas = table.find_all('tr')
                            for i, fila in enumerate(filas):
                                celdas = fila.find_all('td')
                                for j, celda in enumerate(celdas):
                                    if j == 3:  # Columna de "Test Case ID"
                                        celda_valor = celda.get_text(strip=True)
                                        if pd.isnull(celda_valor) or celda_valor == "":
                                            # Ahora insertamos el enlace a Jira en la celda
                                            celda.string = ''  # Limpiamos el contenido de la celda
                                            enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                            # Insertamos el enlace
                                            celda.append(BeautifulSoup(enlace, 'html.parser'))
                                            cont = cont + 1

                            tabla_html_actualizada = str(table)
                            if indice_tabla_a_actualizar < len(tablas):
                                tablas[indice_tabla_a_actualizar].replace_with(
                                    BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                        indice_tabla_a_actualizar = indice_tabla_a_actualizar + 1

                    html_completo_actualizado = str(contenido_completo_soup)

                elif modificar:  # Si modificar es True
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
                        header_texts = [header.get_text().strip().lower()
                                        for header in headers]
                        if "test case id".lower() in header_texts:
                            df = pd.read_html(str(table))[0]
                            columnas_deseadas = ['Test Case ID']
                            df_seleccionado = df[columnas_deseadas]
                            for index, fila in df_seleccionado.iterrows():
                                fila_dict = fila.to_dict()
                                # Ahora, en lugar de solo poner el Test Case ID, ponemos un enlace a Jira
                                fila_dict['Test Case ID'] = f'<a href="https://jira.tid.es/browse/{key[contador]}">{key[contador]}</a>'
                                df.at[index, 0] = fila_dict['Test Case ID']
                                contador = contador + 1

                            data_actualizada = df.values.tolist()
                            filas = table.find_all('tr')
                            for i, fila in enumerate(filas):
                                celdas = fila.find_all('td')
                                for j, celda in enumerate(celdas):
                                    if j == 3:  # Columna de "Test Case ID"
                                        # Insertamos el enlace a Jira en la celda
                                        enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                        celda.string = ''  # Limpiamos el contenido de la celda
                                        # Insertamos el enlace
                                        celda.append(BeautifulSoup(enlace, 'html.parser'))
                                        cont = cont + 1

                            tabla_html_actualizada = str(table)
                            if indice_tabla_a_actualizar < len(tablas):
                                tablas[indice_tabla_a_actualizar].replace_with(
                                    BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                        indice_tabla_a_actualizar = indice_tabla_a_actualizar + 1

                    tabla_html_actualizada = str(tabla_despues_de_frase)
                    tablas[1].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                    html_completo_actualizado = str(contenido_completo_soup)

                # Ahora actualizamos la página con el contenido modificado
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


def crearTCZabbix(jenkinsParameters, contenido):
    listaZabbix = obtenerTextoConf('ZABBIX', contenido, 'Referencia ZABBIX QA', jenkinsParameters["modify"])
    creaJira(jenkinsParameters, 'ZABBIX', listaZabbix)


def crearTCGrafanaPlatform(jenkinsParameters, contenido):
    listaGrafanaPlatform = obtenerTextoConf('GRAFANA PLATFORM', contenido, 'Referencia Grafana Plataforma QA', jenkinsParameters["modify"])
    creaJira(jenkinsParameters, 'GRAFANA PLATFORM', listaGrafanaPlatform)


def crearTCGrafanaPrometheus(jenkinsParameters, contenido):
    listaGrafanaPrometheus = obtenerTextoConf(
        'GRAFANA PROMETHEUS', contenido, 'Referencia GRAFANA PROMETHEUS QA', jenkinsParameters["modify"])
    creaJira(jenkinsParameters, 'GRAFANA PROMETHEUS', listaGrafanaPrometheus)

# Es necesario un número par de tablas para crear correctamente el TC

def crearTCKibana(jenkinsParameters, contenido):
    listaKibana = obtenerTextoConf(
        'KIBANA', contenido, 'Referencia KIBANA QA', jenkinsParameters["modify"])
    print ("\n** KIBANA **\n\n")
    for i in range(0, len(listaKibana), 2):
        creaJira(jenkinsParameters, 'KIBANA',listaKibana[i:i+2])
    modificarTesCaseId(listaIssueKibana, 'KIBANA', jenkinsParameters["modify"])

if __name__ == '__main__':
    jenkinsParameters = getParameters()
    
    page = confluence.get_page_by_title(jenkinsParameters["space"], jenkinsParameters["title"])

    if page:
        page2 = confluence.get_page_by_title(jenkinsParameters["space"], jenkinsParameters["title"], expand='body.storage')
        contenido = page2['body']['storage']['value']

        if jenkinsParameters["zabbix"]:
            crearTCZabbix(jenkinsParameters, contenido)

        if jenkinsParameters["grafana_platform"]:
            crearTCGrafanaPlatform(jenkinsParameters, contenido)

        if jenkinsParameters["grafana_prometheus"]:
            crearTCGrafanaPrometheus(jenkinsParameters, contenido)

        if jenkinsParameters["kibana"]:
            crearTCKibana(jenkinsParameters, contenido)
    
    else:
        raise ValueError("No se encontró la página en Confluence. Verifica los parámetros space y title.")