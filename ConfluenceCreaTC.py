from atlassian import Confluence
import json
from bs4 import BeautifulSoup
import pandas as pd
from jira import JIRA
import copy
from dotenv import load_dotenv
import os


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

# componentName = "Android"
# space='VIDEOTOOLS'
# title='Rebirth Catalog 01 - Loader (Openshift)'

# space='VIDEOTOOLS'
# title='User Extraprovision (Openshift)'

# space='VIDEOTOOLS'
# title='playback-sessions-agent'

# space='VIDEOTOOLS'
# title='top.enablers.cwf_db'

# space='VIDEOTOOLS'
# title='labels-consumer'

# Variables definidas directamente en Jenkins como parámetros
componentName = "top.enablers.cwf_db"

# Obtiene los valores de las variables de entorno desde Jenkins
space = os.getenv("Space")
title = os.getenv("Title")

# Manejo de la variable modificarEnv como un booleano
modificarEnv = os.getenv("Modificar")
if modificarEnv is not None:
    modificarEnv = modificarEnv.lower() == "true"

label = os.getenv("Label")
fixVersion = os.getenv("FixVersion")

# Validación de label y fixVersion
labelEnv = label if label and label.lower() != "none" else None
fixVersionEnv = fixVersion if fixVersion and fixVersion.lower() != "none" else None

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
        # columnas_deseadas = ['PATTERN TO SEARCH','SEVERITY','ALARM NAME','ALARM TEXT','CONDITION','ACTION','Test Case ID']
        # columnas_deseadas_indices = [3,4,5,6,7,8,12]
        columnas_deseadas_indices = [2, 3, 4, 5, 6, 7, 11]
        # df_seleccionado = df[columnas_deseadas]
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
                # nuevo_data = {nombre_claves_ZABBIX[old_key]: value for old_key, value in fila_dict.items() if old_key in nombre_claves_ZABBIX and not pd.isna(value)}
                # if 'Test Case ID' in nombre_claves_ZABBIX and not pd.isna(fila_dict[11]):
                #    nuevo_data[nombre_claves_ZABBIX[11]] = fila_dict[11]
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

        elif modificar == True:
            for index, fila in df_seleccionado.iterrows():
                fila_dict = fila.to_dict()
                fila_dict['Métrica'] = fila_dict['Métrica'].replace(
                    ' ', '\n')
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
                'POD', componentName)
            datosFijos[monitorizacion]['DataSet'] = datosFijos[monitorizacion]['DataSet'].replace(
                'METRICA', metrica)

            return datosFijos

        elif monitorizacion == 'GRAFANA PROMETHEUS':
            # Default to empty string if not present
            dbInflux = datosConf.get('DB En Influx', '')
            # Default to empty string if not present
            medida = datosConf.get('Medida', '')
            # Default to empty string if not present
            metrica = datosConf.get('Métrica', '')
            # Default to empty string if not present
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
                'METRIC', componentName)

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


def creaJira(project, monitorizacion, datosConfluence, modificar, componente, label=None, fixVersion=None):
    options = {'server': 'https://jira.tid.es/'}
    userJira = 'qasupport'
    passJIRA = 'temporal'
    jira = jiraConnection(options, userJira, passJIRA)

    if monitorizacion == 'ZABBIX':
        listaIssueZabbix = []
        for dato in datosConfluence:
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, dato, datosFijos, componente)

            if fixVersion is not None:
                fixVersionSplit = fixVersion.split(",")
                fixVersionFinal = []
                for fv in fixVersionSplit:
                    temporal = {'name': fv}
                    fixVersionFinal.append(temporal)
            else:
                fixVersionFinal = None

            jiraIssue = JiraIssue("", "Test Case", "", createSummary(monitorizacion, datosFijos, dato, componente), label, componente, datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'], datosFijos[monitorizacion][
                                        'ExecutionMode'], datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'], datosFijos[monitorizacion][
                                        'TestPriority'], datosFijos[monitorizacion]['TestReviewed'],
                                    "", datosFijos[monitorizacion]['PreRequisites'], datosFijos[monitorizacion]['DataSet'],
                                    datosFijos[monitorizacion]['Procedure'], datosFijos[monitorizacion]['ExpectedResult'], project, fixVersionFinal)

            linked_ticket_zabbix = os.getenv("Zabbix Is Tested By")
            
            if modificar == True:
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
                    listaIssueZabbix.append(ticket_existente)
                    if linked_ticket_zabbix:
                        ticket_existente.add_link(type='Tested By', issue=linked_ticket_zabbix)
                        print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket_zabbix}")
                else:
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    print(f'Ticket {jiraIssue.issueKey} creado.')
                    print(jiraIssue.summary)
                    print(jiraIssue.issueKey)
                    listaIssueZabbix.append(str(jiraIssue.issueKey))
                    if linked_ticket_zabbix:
                        ticket_existente.add_link(type='Tested By', issue=linked_ticket_zabbix)
                        print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket_zabbix}")

            elif modificar == False:
                if 'Test Case ID' in dato:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(
                        jira, key)
                    if ticket_existente:
                        print("TC EXISTENTE: "+str(key))
                    else:
                        print(jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(
                            fields=createIssueDict(jiraIssue))
                        listaIssueZabbix.append(str(jiraIssue.issueKey))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.issueKey)
                        if linked_ticket_zabbix:
                            ticket_existente.add_link(type='Tested By', issue=linked_ticket_zabbix)
                            print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket_zabbix}")
                else:
                    print(jiraIssue.summary)
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    listaIssueZabbix.append(str(jiraIssue.issueKey))
                    print(f'Ticket {jiraIssue.issueKey} creado.')
                    print(jiraIssue.issueKey)
                    if linked_ticket_zabbix:
                        ticket_existente.add_link(type='Tested By', issue=linked_ticket_zabbix)
                        print(f"Ticket {ticket_existente.key} enlazado con {linked_ticket_zabbix}")

        modificarTesCaseId(listaIssueZabbix, 'ZABBIX', modificar)

    elif monitorizacion == 'GRAFANA PLATFORM':
        listaIssueGrafanaPlatform = []
        for dato in datosConfluence:
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, dato, datosFijos, componente)

            if fixVersion is not None:
                fixVersionSplit = fixVersion.split(",")
                fixVersionFinal = []
                for fv in fixVersionSplit:
                    temporal = {'name': fv}
                    fixVersionFinal.append(temporal)
            else:
                fixVersionFinal = None

            jiraIssue = JiraIssue("", "Test Case", "", createSummary(monitorizacion, datosFijos, dato, componente), label, componente, datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'], datosFijos[monitorizacion][
                                        'ExecutionMode'], datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'], datosFijos[monitorizacion][
                                        'TestPriority'], datosFijos[monitorizacion]['TestReviewed'],
                                    datosFijos[monitorizacion]['Description'], datosFijos[monitorizacion][
                                        'PreRequisites'], datosFijos[monitorizacion]['DataSet'],
                                    "", "", project, fixVersionFinal)

            if modificar == True:
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
                    listaIssueGrafanaPlatform.append(ticket_existente)
                else:
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    print(f'Ticket {jiraIssue.issueKey} creado.')
                    print(jiraIssue.summary)
                    print(jiraIssue.issueKey)
                    listaIssueGrafanaPlatform.append(
                        str(jiraIssue.issueKey))

            elif modificar == False:
                key = dato['Test Case ID']
                ticket_existente = buscar_ticket_existente_por_key(
                    jira, key)
                if ticket_existente:
                    print("TC EXISTENTE: "+str(key))
                else:
                    print(jiraIssue.summary)
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    listaIssueGrafanaPlatform.append(
                        str(jiraIssue.issueKey))
                    print(jiraIssue.issueKey)

        modificarTesCaseId(listaIssueGrafanaPlatform,
                            'GRAFANA PLATFORM', modificar)

    elif monitorizacion == 'GRAFANA PROMETHEUS':
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
                monitorizacion, {"Metric": metric_name}, datosFijos, componente)
            dataset_content = datosFijos[monitorizacion]['DataSet']

            new_table = "\n\n\n|| Metric ||\n"
            for param in params:
                new_table += f"| {param} |\n"

            dataset_content += "\n" + new_table

            if fixVersion is not None:
                fixVersionSplit = fixVersion.split(",")
                fixVersionFinal = [{'name': fv} for fv in fixVersionSplit]
            else:
                fixVersionFinal = None

            jiraIssue = JiraIssue(
                "", "Test Case", "",
                createSummary(monitorizacion, datosFijos, {
                                "Metric": metric_name}, componente),
                label, componente,
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
                "", "", project, fixVersionFinal
            )

            if metric_name not in created_tickets:
                if modificar:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(
                        jira, key)
                    if ticket_existente:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(
                            f'Ticket {ticket_existente.key} actualizado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueGrafanaPrometheus.append(
                            ticket_existente)
                    else:
                        jiraIssue.issueKey = jira.create_issue(
                            fields=createIssueDict(jiraIssue))
                        created_tickets.add(metric_name)
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueGrafanaPrometheus.append(
                            str(jiraIssue.issueKey))
                else:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(
                        jira, key)
                    if ticket_existente:
                        print("TC EXISTENTE: " + str(dato['Test Case ID']))
                    else:
                        print(jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(
                            fields=createIssueDict(jiraIssue))
                        created_tickets.add(metric_name)
                        listaIssueGrafanaPrometheus.append(
                            str(jiraIssue.issueKey))
                        print(jiraIssue.issueKey)

        modificarTesCaseId(listaIssueGrafanaPrometheus,
                               'GRAFANA PROMETHEUS', modificar)

    elif monitorizacion == 'KIBANA':
        if fixVersion is not None:
            fixVersionSplit = fixVersion.split(",")
            fixVersionFinal = []
            for fv in fixVersionSplit:
                temporal = {'name': fv}
                fixVersionFinal.append(temporal)
        else:
            fixVersionFinal = None

        if len(datosConfluence[0]) > 1:
            for dato in datosConfluence[0]:
                datosFijos = cargarJson('datosFijos.json')
                datosFijos = actualizarDatosFijos(
                    monitorizacion, datosConfluence, datosFijos, componente, dato['functionName'])

                jiraIssue = JiraIssue("", "Test Case", "", createSummary(monitorizacion, datosFijos, datosConfluence, componente, dato['functionName']), label, componente, datosFijos[monitorizacion]['TestType'],
                                        datosFijos[monitorizacion]['TestScope'], datosFijos[monitorizacion][
                                            'ExecutionMode'], datosFijos[monitorizacion]['AutomationCandidate'],
                                        datosFijos[monitorizacion]['Regression'], datosFijos[monitorizacion][
                                            'TestPriority'], datosFijos[monitorizacion]['TestReviewed'],
                                        "", "", datosFijos[monitorizacion]['DataSet'],
                                        "", datosFijos[monitorizacion]['ExpectedResult'], project, fixVersionFinal)

                if modificar == True:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(
                        jira, key)
                    if ticket_existente:
                        fields_to_update = createIssueDict(jiraIssue)
                        fields_to_update.pop('key', None)
                        ticket_existente.update(fields=fields_to_update)
                        print(
                            f'Ticket {ticket_existente.key} actualizado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueKibana.append(ticket_existente)
                    else:
                        jiraIssue.issueKey = jira.create_issue(
                            fields=createIssueDict(jiraIssue))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.summary)
                        print(jiraIssue.issueKey)
                        listaIssueKibana.append(str(jiraIssue.issueKey))
                elif modificar == False:
                    key = dato['Test Case ID']
                    ticket_existente = buscar_ticket_existente_por_key(
                        jira, key)
                    if ticket_existente:
                        print("TC EXISTENTE: "+str(key))
                    else:
                        print(jiraIssue.summary)
                        jiraIssue.issueKey = jira.create_issue(
                            fields=createIssueDict(jiraIssue))
                        listaIssueKibana.append(str(jiraIssue.issueKey))
                        print(f'Ticket {jiraIssue.issueKey} creado.')
                        print(jiraIssue.issueKey)

        else:
            datosFijos = cargarJson('datosFijos.json')
            datosFijos = actualizarDatosFijos(
                monitorizacion, datosConfluence, datosFijos, componente, datosConfluence[0][0]['functionName'])

            jiraIssue = JiraIssue("", "Test Case", "", createSummary(monitorizacion, datosFijos, datosConfluence, componente, datosConfluence[0][0]['functionName']), label, componente, datosFijos[monitorizacion]['TestType'],
                                    datosFijos[monitorizacion]['TestScope'], datosFijos[monitorizacion][
                                        'ExecutionMode'], datosFijos[monitorizacion]['AutomationCandidate'],
                                    datosFijos[monitorizacion]['Regression'], datosFijos[monitorizacion][
                                        'TestPriority'], datosFijos[monitorizacion]['TestReviewed'],
                                    "", "", datosFijos[monitorizacion]['DataSet'],
                                    "", datosFijos[monitorizacion]['ExpectedResult'], project, fixVersionFinal)

            if modificar == True:
                key = datosConfluence[0][0]['Test Case ID']
                ticket_existente = buscar_ticket_existente_por_key(
                    jira, key)
                if ticket_existente:
                    fields_to_update = createIssueDict(jiraIssue)
                    fields_to_update.pop('key', None)
                    ticket_existente.update(fields=fields_to_update)
                    print(f'Ticket {ticket_existente.key} actualizado.')
                    print(jiraIssue.summary)
                    print(jiraIssue.issueKey)
                    listaIssueKibana.append(ticket_existente)
                else:
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    print(f'Ticket {jiraIssue.issueKey} creado.')
                    print(jiraIssue.summary)
                    print(jiraIssue.issueKey)
                    listaIssueKibana.append(str(jiraIssue.issueKey))
            else:
                key = datosConfluence[0][0]['Test Case ID']
                ticket_existente = buscar_ticket_existente_por_key(
                    jira, key)
                if ticket_existente:
                    print("TC EXISTENTE: "+str(key))
                else:
                    print(jiraIssue.summary)
                    jiraIssue.issueKey = jira.create_issue(
                        fields=createIssueDict(jiraIssue))
                    listaIssueKibana.append(str(jiraIssue.issueKey))
                    print(f'Ticket {jiraIssue.issueKey} creado.')
                    print(jiraIssue.issueKey)


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

        if monitorizacion == 'ZABBIX':
            space = os.getenv("space")
            title = os.getenv("title")
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
            space = 'QAVIDEO'
            title = 'pruebas QA'
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
                                # celda.string = str(data_actualizada[i-1][j])
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
                                # celda.string = str(data_actualizada[i-1][j])
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
            space = os.getenv("space")
            title = os.getenv("title")
            page = confluence.get_page_by_title(space, title)

            if page:
                # Obtén todo el contenido de la página
                page2 = confluence.get_page_by_title(space, title, expand='body.storage')
                contenido = page2['body']['storage']['value']

                # Parseamos el contenido completo con BeautifulSoup
                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')

                # Buscamos la referencia "Referencia GRAFANA PROMETHEUS QA" en el contenido
                contenidoSplit = contenido.split("Referencia GRAFANA PROMETHEUS QA")
                if len(contenidoSplit) < 2:
                    print("No se encontró la referencia 'Referencia GRAFANA PROMETHEUS QA'.")
                    return

                # Trabajamos con la parte después de la referencia
                contenido_despues_referencia = contenidoSplit[1]
                contenido_despues_soup = BeautifulSoup(contenido_despues_referencia, 'html.parser')

                # Buscamos todas las tablas en la parte después de la referencia
                tablas = contenido_despues_soup.find_all('table')

                # Tomamos la primera tabla (la que queremos modificar)
                tabla_despues_de_frase = tablas[0]

                # Convertimos la tabla en un DataFrame para manipularla
                df = pd.read_html(str(tabla_despues_de_frase))[0]
                # Eliminamos la fila de encabezados original
                df = df.drop(df.index[0])
                # Las columnas que nos interesan
                columnas_deseadas_indices = [0, 1, 3, 6, 7, 13]

                max_index = df.shape[1] - 1
                if all(0 <= idx <= max_index for idx in columnas_deseadas_indices):
                    columnas_deseadas_nombres = [
                        df.columns[idx] for idx in columnas_deseadas_indices]
                    df_seleccionado = df[columnas_deseadas_nombres]
                    df_seleccionado.columns = columnas_deseadas_indices
                else:
                    print(f"Algunos índices están fuera del rango. El rango válido es 0 a {max_index}.")
                    return

                # Aquí empieza la actualización de las celdas según 'modificar'
                if not modificar:
                    contador = 0
                    for index, fila in df_seleccionado.iterrows():
                        fila_dict = fila.to_dict()
                        if pd.isnull(fila_dict[13]) or fila_dict[13] == "":
                            if contador == len(key):
                                break
                            # Insertamos la clave en la columna 13
                            fila_dict[13] = key[contador]
                            df.at[index, 13] = fila_dict[13]
                            contador += 1

                    # Actualizamos el HTML de la tabla en el DOM de BeautifulSoup
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
                                else:
                                    print("No se cambia el valor")

                            if j == 13:  # La columna que queremos modificar
                                celda_valor = celda.get_text(strip=True)
                                if pd.isnull(celda_valor) or celda_valor == "":
                                    if valorMetric != valorMetricAux:
                                        cont += 1
                                        valorMetricAux = valorMetric
                                    if cont == len(key):
                                        break
                                    # Modificar la celda con el enlace de Jira
                                    enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                    celda.string = ''  # Limpiar el contenido de la celda
                                    # Insertar el enlace
                                    celda.append(BeautifulSoup(enlace, 'html.parser'))

                    # Aquí comienza la lógica para combinar las celdas de la columna 13 con el mismo valor
                    celdas_fila_13 = []
                    for fila in filas:
                        celdas = fila.find_all('td')
                        if len(celdas) > 13:
                            celdas_fila_13.append(celdas[13])

                    i = 0
                    while i < len(celdas_fila_13):
                        valor_celda = celdas_fila_13[i].get_text(strip=True)
                        j = i + 1
                        while j < len(celdas_fila_13) and celdas_fila_13[j].get_text(strip=True) == valor_celda:
                            # Si las celdas tienen el mismo valor, combinamos
                            # Eliminamos la celda repetida
                            celdas_fila_13[j].extract()
                            j += 1
                        # Actualizamos la celda original con el atributo rowspan para cubrir las celdas combinadas
                        if j > i + 1:
                            celdas_fila_13[i]['rowspan'] = j - \
                                i  # Combinamos las celdas
                        i = j

                    # Actualizamos el HTML de la tabla modificada
                    tabla_html_actualizada = str(tabla_despues_de_frase)
                    tablas[0].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                elif modificar:
                    contador = 0
                    for index, fila in df_seleccionado.iterrows():
                        fila_dict = fila.to_dict()
                        # Actualizamos la columna 13 con la nueva clave
                        fila_dict[13] = key[contador]
                        df.at[index, 13] = fila_dict[13]
                        contador += 1

                    filas = tabla_despues_de_frase.find_all('tr')
                    cont = 0
                    for i, fila in enumerate(filas):
                        celdas = fila.find_all('td')
                        for j, celda in enumerate(celdas):
                            if j == 13:
                                # Modificar la celda con el enlace de Jira
                                enlace = f'<a href="https://jira.tid.es/browse/{key[cont]}">{key[cont]}</a>'
                                celda.string = ''  # Limpiar el contenido de la celda
                                # Insertar el enlace
                                celda.append(BeautifulSoup(enlace, 'html.parser'))
                                cont += 1

                    # Aquí comienza la lógica para combinar las celdas de la columna 13 con el mismo valor
                    celdas_fila_13 = []
                    for fila in filas:
                        celdas = fila.find_all('td')
                        if len(celdas) > 13:
                            celdas_fila_13.append(celdas[13])

                    i = 0
                    while i < len(celdas_fila_13):
                        valor_celda = celdas_fila_13[i].get_text(strip=True)
                        j = i + 1
                        while j < len(celdas_fila_13) and celdas_fila_13[j].get_text(strip=True) == valor_celda:
                            # Si las celdas tienen el mismo valor, combinamos
                            # Eliminamos la celda repetida
                            celdas_fila_13[j].extract()
                            j += 1
                        # Actualizamos la celda original con el atributo rowspan para cubrir las celdas combinadas
                        if j > i + 1:
                            celdas_fila_13[i]['rowspan'] = j - \
                                i  # Combinamos las celdas
                        i = j

                    # Actualizamos el HTML de la tabla modificada
                    tabla_html_actualizada = str(tabla_despues_de_frase)
                    tablas[1].replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))

                contenido_completo_soup = BeautifulSoup(contenido, 'html.parser')

                # Busca la referencia "Referencia GRAFANA PROMETHEUS QA"
                frase = "Referencia GRAFANA PROMETHEUS QA"
                frase_tag = contenido_completo_soup.find(string=frase)

                # Encuentra la tabla inmediatamente después de la referencia
                tabla_despues_de_frase = None
                if frase_tag:
                    siguiente_elemento = frase_tag.find_next()
                    while siguiente_elemento:
                        if siguiente_elemento.name == 'table':
                            tabla_despues_de_frase = siguiente_elemento
                            break
                        siguiente_elemento = siguiente_elemento.find_next()

                if tabla_despues_de_frase:
                    # Reemplaza la tabla encontrada con la tabla actualizada
                    tabla_despues_de_frase.replace_with(BeautifulSoup(tabla_html_actualizada, 'html.parser'))
                else:
                    print("Error: No se encontró una tabla después de la referencia.")
                    return

                # Convertimos todo el contenido actualizado en HTML
                html_completo_actualizado = str(contenido_completo_soup)

                # Actualizamos la página completa en Confluence
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
            space = os.getenv("space")
            title = os.getenv("title")
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


def crearTCZabbix(project, contenido, modificar, componente, label=None, fixVersion=None):
    listaZabbix = obtenerTextoConf(
        'ZABBIX', contenido, 'Referencia ZABBIX QA', modificar)
    creaJira(project, 'ZABBIX', listaZabbix,
             modificar, componente, label, fixVersion)


def crearTCGrafanaPlatform(project, contenido, modificar, componente, label=None, fixVersion=None):
    listaGrafanaPlatform = obtenerTextoConf(
        'GRAFANA PLATFORM', contenido, 'Referencia Grafana Plataforma QA', modificar)
    creaJira(project, 'GRAFANA PLATFORM', listaGrafanaPlatform,
             modificar, componente, label, fixVersion)


def crearTCGrafanaPrometheus(project, contenido, modificar, componente, label=None, fixVersion=None):
    listaGraganaPrometheus = obtenerTextoConf(
        'GRAFANA PROMETHEUS', contenido, 'Referencia GRAFANA PROMETHEUS QA', modificar)
    creaJira(project, 'GRAFANA PROMETHEUS', listaGraganaPrometheus,
             modificar, componente, label, fixVersion)

# Es necesario un número par de tablas para crear correctamente el TC


def crearTCKibana(project, contenido, modificar, componente, label=None, fixVersion=None):
    listaKibana = obtenerTextoConf(
        'KIBANA', contenido, 'Referencia KIBANA QA', modificar)
    for i in range(0, len(listaKibana), 2):
        creaJira(project, 'KIBANA',
                 listaKibana[i:i+2], modificar, componente, label, fixVersion)
    modificarTesCaseId(listaIssueKibana, 'KIBANA', modificar)


def main(project, modificar, componente, label=None, fixVersion=None):
    space = os.getenv("Space")
    title = os.getenv("Title")
    page = confluence.get_page_by_title(space, title)

    if page:
        page2 = confluence.get_page_by_title(
            space, title, expand='body.storage')
        contenido = page2['body']['storage']['value']

        # Leer los parámetros booleanos de Jenkins
        zabbix = os.getenv("ZABBIX", "false").lower() == "true"
        grafana_platform = os.getenv("GRAFANA PLATAFORMA", "false").lower() == "true"
        grafana_prometheus = os.getenv("GRAFANA PROMETHEUS", "false").lower() == "true"
        kibana = os.getenv("KIBANA", "false").lower() == "true"

        # Lógica para crear TC según los parámetros activados
        if zabbix:
            crearTCZabbix(project, contenido, modificar, componente, label, fixVersion)

        if grafana_platform:
            crearTCGrafanaPlatform(project, contenido, modificar, componente, label, fixVersion)

        if grafana_prometheus:
            crearTCGrafanaPrometheus(project, contenido, modificar, componente, label, fixVersion)

        if kibana:
            crearTCKibana(project, contenido, modificar, componente, label, fixVersion)

        # Caso especial: Si todos están activados, considerar 'ALL'
        if zabbix and grafana_platform and grafana_prometheus and kibana:
            crearTCZabbix(project, contenido, modificar, componente, label, fixVersion)
            crearTCGrafanaPlatform(project, contenido, modificar, componente, label, fixVersion)
            crearTCGrafanaPrometheus(project, contenido, modificar, componente, label, fixVersion)
            crearTCKibana(project, contenido, modificar, componente, label, fixVersion)

    else:
        raise ValueError("No se encontró la página en Confluence. Verifica los parámetros space y title.")


# main ("USERSAPITC","GRAFANA PLATFORM",False,"top.user.extraprovision",None,None)
# main ("MBJIRATEST","GRAFANA PROMETHEUS",False,"Android",None,None)
# main ("MBJIRATEST",'ZABBIX',False,"DATAHUB",None,None)

# main ("MBJIRATEST","GRAFANA PROMETHEUS",False,"Android",None,None)


# main ("ORCHTC",'ZABBIX',False,"top.service.config.api",None,"Orquestador_1.23,FEServices_24.12")
# main ("MBJIRATEST","GRAFANA PLATFORM",False,"top.service.config.api",None,"Orquestador_1.23,FEServices_24.12")
# main ("ORCHTC","GRAFANA PROMETHEUS",False,"top.service.config.api",None,"Orquestador_1.23,FEServices_24.12")
# main ("ORCHTC",'KIBANA',False,"top.service.config.api",None,"Orquestador_1.23,FEServices_24.12")

# main ("MBJIRATEST",'ZABBIX',False,"Android",None,None)
# main ("MBJIRATEST","GRAFANA PLATFORM",False,"Android",None,None)
# main ("MBJIRATEST",'KIBANA',False,"Android",None,None)

main(os.getenv("Project"),modificarEnv, os.getenv("Componente"), labelEnv, fixVersionEnv)