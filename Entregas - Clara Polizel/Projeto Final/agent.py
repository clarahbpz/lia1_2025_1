import datetime
import os.path
from google.adk.agents import Agent
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError 

from dotenv import load_dotenv
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    creds = None
    client_secret_path = os.path.join(os.path.dirname(__file__), 'client_secret.json') 
    token_path = os.path.join(os.path.dirname(__file__), 'token.json')

    if not os.path.exists(client_secret_path):
        print(f"ATENÇÃO: O arquivo '{client_secret_path}' não foi encontrado. A Google Agenda não poderá ser acessada.")
        return None 

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Erro ao iniciar o fluxo de autenticação: {e}")
                return None
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f'Ocorreu um erro ao conectar à Google Calendar API: {error}')
        return None

def get_events(num_events: Optional[int] = None, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> str:
    service = get_google_calendar_service()
    if not service:
        return "Não foi possível conectar à sua Google Agenda. Por favor, verifique as credenciais e tente novamente."

    time_min = None
    time_max = None
    max_results = None
    query_description = "eventos"

    if num_events is not None:
        if num_events <= 0:
            return "O número de eventos deve ser maior que zero."
        time_min = datetime.datetime.utcnow().isoformat() + 'Z'
        max_results = num_events
        query_description = f"os próximos {num_events} eventos"
    elif start_date_str and end_date_str:
        try:
            start_dt = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt = datetime.datetime.strptime(end_date_str, '%Y-%m-%d') + datetime.timedelta(days=1, seconds=-1)
            
            time_min = start_dt.isoformat() + 'Z'
            time_max = end_dt.isoformat() + 'Z'
            query_description = f"eventos de {start_date_str} a {end_date_str}"
        except ValueError:
            return "Formato de data inválido. Use 'AAAA-MM-DD'."
    else:
        return "Por favor, especifique quantos eventos você quer ver ou um intervalo de datas (ex: 'hoje', 'essa semana')."

    try:
        print(f'Buscando {query_description}...')
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f'Nenhum evento encontrado para {query_description}.'

        event_list_str = f"Seus {query_description}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            event_list_str += f"- {event['summary']} (De: {start}, Até: {end})\n"
        return event_list_str
    except HttpError as error:
        return f'Ocorreu um erro ao buscar os eventos na Google Calendar API: {error}. Se o problema persistir, por favor, verifique suas credenciais. Posso te oferecer algumas dicas de organização enquanto isso?'
    except Exception as e:
        return f'Ocorreu um erro inesperado ao buscar eventos: {e}. Posso te oferecer algumas dicas de organização enquanto isso?'

def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> str:
    service = get_google_calendar_service()
    if not service:
        return "Não foi possível conectar à sua Google Agenda para criar o evento. Por favor, verifique as credenciais e tente novamente."

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'America/Sao_Paulo',
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f'Evento "{event.get("summary")}" criado com sucesso! Link: {event.get("htmlLink")}'
    except HttpError as error:
        return f'Ocorreu um erro ao criar o evento: {error}. Verifique se os horários estão no formato correto e se você tem permissão. Posso te oferecer dicas de como agendar tarefas eficientemente?'
    except Exception as e:
        return f'Ocorreu um erro inesperado ao criar o evento: {e}. Posso te oferecer dicas de como agendar tarefas eficientemente?'

def delete_calendar_event(event_id: str) -> str:
    service = get_google_calendar_service()
    if not service:
        return "Não foi possível conectar à sua Google Agenda para deletar o evento. Por favor, verifique as credenciais e tente novamente."

    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return f'Evento com ID "{event_id}" deletado com sucesso!'
    except HttpError as error:
        if error.resp.status == 404:
            return f'Evento com ID "{event_id}" não encontrado ou já foi deletado.'
        return f'Ocorreu um erro ao deletar o evento: {error}. Posso te oferecer dicas de organização enquanto isso?'
    except Exception as e:
        return f'Ocorreu um erro inesperado ao deletar o evento: {e}. Posso te oferecer dicas de organização enquanto isso?'


root_agent = Agent(
    name="RotinaInteligente",
    model="gemini-2.0-flash",
    description="Seu assistente pessoal para otimizar e organizar sua rotina diária.",
    instruction=f"""
    Você é o **Agente Rotina Inteligente**, um especialista em gestão de tempo e produtividade.
    Seu objetivo principal é **ajudar o usuário a organizar sua rotina, identificar lacunas, sugerir otimizações de tempo e gerenciar eventos em sua Google Agenda**.

    **Sua inteligência deve ser aplicada para:**
    * Analisar a agenda do usuário: Buscar compromissos, identificar horários livres ou sobrepostos (se tiver acesso).
    * Oferecer sugestões proativas de produtividade e organização, gerando dicas.
    * Gerar dicas de priorização e gestão de tempo.
    * Criar, modificar e deletar eventos na Google Agenda.
    * Fornecer um resumo claro da rotina.

    **Suas ferramentas para interagir com a Google Agenda são:**
    * `get_events(num_events: Optional[int] = None, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None)`: Use para buscar eventos. Você **deve** fornecer **OU** `num_events` **OU** `start_date_str` e `end_date_str`.
        * Para "hoje": Calcule `start_date_str = datetime.date.today().isoformat()` e `end_date_str = datetime.date.today().isoformat()`.
        * Para "amanhã": Calcule `start_date_str = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()` e `end_date_str = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()`.
        * Para "esta semana", "próxima semana", "este mês", "próximo mês", "próximos N dias": Siga a lógica de `datetime` e `timedelta` para calcular `start_date_str` e `end_date_str`.
        * Lembre-se: `datetime.date.today()` te dá a data de hoje (agora é {datetime.date.today().isoformat()}).
    * `Calendar(summary: str, start_time: str, end_time: str, description: str = "")`: Use para criar eventos. `start_time` e `end_time` devem estar no formato ISO 8601 completo (ex: "2025-06-18T09:00:00-03:00"). Use o fuso horário 'America/Sao_Paulo'.
    * `delete_calendar_event(event_id: str)`: Use para deletar eventos. Você precisará do ID do evento.

    **Sua capacidade de gerar dicas de rotina e produtividade:**
    * Você pode **gerar essas dicas diretamente** com base no seu conhecimento.
    * Quando o usuário pedir conselhos sobre produtividade, organização, priorização, gestão de tempo, como lidar com distrações, ou qualquer outro tópico relacionado à rotina:
        * Gere uma dica relevante e útil diretamente na sua resposta. Pense em estratégias como a Técnica Pomodoro, Matriz de Eisenhower, Regra 80/20, métodos para evitar distrações, ou como visualizar o tempo disponível.
        * Seja o mais específico possível com base no pedido do usuário.

    **Seu tom deve ser:**
    * Eficiente e objetivo: Focado em soluções e otimização.
    * Prestativo e proativo: Antecipando as necessidades do usuário.
    * Claro e conciso: Evitando redundâncias.

    **Diretrizes de Interação:**
    * Sempre comece a conversa perguntando como você pode ajudar a otimizar a rotina do usuário. Ex: "Olá! Sou o Agente Rotina Inteligente. Como posso te ajudar a otimizar sua rotina hoje?"
    * **Quando o usuário pedir para ver a agenda, criar, mover ou deletar eventos:**
        * Use as ferramentas da Google Agenda (`get_events`, `Calendar`, `delete_calendar_event`).
        * Se a ferramenta retornar uma mensagem de erro de conexão ou de API, você deve informar o usuário sobre a falha e **sugerir que, em vez disso, você pode oferecer dicas de organização ou priorização**. Ex: "Desculpe, não consegui completar essa ação na sua Google Agenda devido a um erro. Posso te dar algumas dicas sobre como planejar melhor?"
    * **Quando o usuário pedir para agendar algo, SEMPRE peça os detalhes completos:** o que é o evento, horário de início e fim no formato de hora/minuto. Você é responsável por formatar isso para ISO 8601. Confirme antes de criar: "Entendi, você gostaria de agendar '[sumário]' de [hora início] a [hora fim]? Posso criar esse evento para você?"
    * **Quando o usuário pedir para deletar um evento, SEMPRE peça confirmação** e, se possível, o ID ou o nome exato do evento e a data para evitar enganos. Ex: "Você gostaria de deletar o evento '[nome]' de [data]? Posso fazer isso?" Se o usuário não fornecer o ID, peça para ele buscar os eventos primeiro para obter o ID.
    * **Quando o usuário pedir algo genérico sobre rotina ou produtividade, ou se ele aceitar sua oferta de dicas:** Gere uma dica diretamente na sua resposta.
    * Seja educado e responda de forma natural.
    """,
    tools=[get_events, create_calendar_event, delete_calendar_event] # Adicionada delete_calendar_event
)