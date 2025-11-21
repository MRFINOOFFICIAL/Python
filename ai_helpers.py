# ai_helpers.py
import os
import openai
import asyncio

# Asegúrate de tener tu OPENAI_API_KEY en los Secrets de Replit
openai.api_key = os.getenv("OPENAI_API_KEY")

async def ask_openai(prompt, system=""):
    """
    Función para preguntar a OpenAI usando la nueva API >=1.0.0
    - prompt: el texto de la pregunta
    - system: instrucciones del sistema (rol del asistente)
    Devuelve el texto generado.
    """
    loop = asyncio.get_event_loop()

    def run_openai():
        response = openai.ChatCompletion.create(
            model="gpt-4",  # o "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.5
        )
        return response.choices[0].message.content

    return await loop.run_in_executor(None, run_openai)
