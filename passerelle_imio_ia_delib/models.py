from builtins import str

import json
import requests
from django.db import models
from django.http import Http404
from django.http import HttpResponse
from django.urls import reverse
from passerelle.base.models import BaseResource
from passerelle.utils.api import endpoint
from passerelle.utils.jsonresponse import APIError
from requests.exceptions import ConnectionError


class IADelibConnector(BaseResource):
    """
    Connecteur iA.Delib
    """
    url = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="URL",
        help_text="URL de l'application iA.Delib",
    )
    username = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Utilisateur",
    )
    password = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Mot de passe",
    )
    api_description = "Connecteur permettant d'intéragir avec une instance d'iA.Delib"
    category = "Connecteurs iMio"
    files_keys = ["simple_files", "workflow_files", "blocs_of_files"]

    class Meta:
        verbose_name = "Connecteur iA.Delib"

    @property
    def session(self):
        session = requests.Session()
        session.auth = (self.username, self.password)
        session.headers.update({"Accept": "application/json"})
        return session

    @endpoint(
        perm="can_access",
        description="Valider la connexion entre iA.Delib et Publik",
    )
    def test(self, request):
        url = self.url  # Url et endpoint à contacter
        return self.session.get(url).json()

    @endpoint(
        methods=["get"],
        name="read-item",
        description="Tester un GET sur Delib",
        parameters={
            "uid": {
                "description": "Identifiant d'un Point",
                "example_value": "bce166cfb27946b58aff9ecfa27367fc",
            },
            "config_id": {
                "description": "Identifiant de la config de l'instance iA.Delib",
                "example_value": "meeting-config-college",
            },
        },
        perm="can_access",
    )
    def read_item(self, request, uid, config_id):
        url = f"{self.url}@item"  # Url et endpoint à contacter
        params = {
            "UID": uid,
            "config_id": config_id,
        }  # UID de mon point à récupérer et configuration de l'instance iA.Delib.
        try:
            response_json = self.session.get(url, params=params).json()
        except Exception as e:
            raise APIError(
                str(e),
                http_status=405,
            )
        return response_json

    @endpoint(
        methods=["get"],
        name="search-items",
        description="GET @search sur Delib",
        long_description="Prend un dictionnaire et renvoie une liste d'items",
        perm="can_access",
    )
    def search_items(self, request, **kwargs):
        url = f"{self.url}@search"  # Url et endpoint à contacter
        params = kwargs
        try:
            response_json = self.session.get(url, params=params).json()
        except Exception as e:
            raise APIError(
                str(e),
                http_status=405,
            )
        return response_json

    def list_simple_files(self, fields, files):
        result = []
        for file in files:
            if fields[file]:
                result.append(fields[file])
        return result

    def list_files_of_blocs(self, fields, blocs_of_files):
        result = []
        for bloc_of_files in blocs_of_files:
            if fields[bloc_of_files]:
                for file in fields[f"{bloc_of_files}_raw"]:
                    result.append(file['fichier'])
        return result

    def structure_annexes(self, files):
        result = []
        for file in files:
            structured_file = {
                "@type": "annex",
                "title": file["filename"],
                "content_category": "annexe",
                "file": {
                    "data": file["content"],
                    "filename": file["filename"]
                }
            }
            result.append(structured_file)
        return result


    def get_annexes(self, post_data, demand):
        fields = demand.json()['fields']
        annexes = []
        if "simple_files" in post_data.keys():
            annexes.extend(self.list_simple_files(fields, post_data['simple_files']))
        if "workflow_files" in post_data.keys():
            annexes.extend(self.list_simple_files(demand.json()['workflow']['fields'], post_data['workflow_files']))
        if "blocs_of_files" in post_data.keys():
            annexes.extend(self.list_files_of_blocs(fields, post_data['blocs_of_files']))
        return annexes

    @endpoint(
        methods=["post"],
        name="create-item",
        description="Tester un POST sur Delib local",
        perm="can_access",
    )
    def create_item(self, request):
        files_keys = self.files_keys
        url = f"{self.url}@item"  # Url et endpoint à contacter
        post_data = json.loads(request.body)
        demand = requests.get(
            post_data['api_url'],
            auth=(self.username, self.password),
            headers={"Accept": "application/json"}
        )
        if len([x for x in post_data.keys() if x in files_keys]) > 0:
            annexes = self.get_annexes(post_data, demand)
            if len(annexes) > 0:
                post_data["__children__"] = self.structure_annexes(annexes)
        try:
            response_json = self.session.post(
                url,
                headers={"Content-Type": "application/json"},
                json=post_data,
            ).json()
        except Exception as e:
            raise APIError(
                str(e),
                http_status=405,
            )
        return response_json

    @endpoint(
        methods=["post"],
        name="add-annexes",
        description="POST @annex sur un item Delib",
        long_description="Ajout de pièces jointes sur un élément existant de Délib",
        perm="can_access",
    )
    def add_annexes(self, request):
        files_keys = self.files_keys
        post_data = json.loads(request.body)
        url = f"{self.url}@annex/{post_data['UID']}"  # Url et endpoint à contacter
        # Demande concernée
        demand = requests.get(
            post_data['api_url'],
            auth=(self.username, self.password),
            headers={"Accept": "application/json"}
        )
        if len([x for x in post_data.keys() if x in files_keys]) > 0:
            annexes = self.get_annexes(post_data, demand)
            if len(annexes) > 0:
                structured_annexes = self.structure_annexes(annexes)
                titles = ' '.join([annex['title'] for annex in structured_annexes])
                self.logger.info(f"Début de l'envoi des documents {titles}")
                reponses = {"data": []}
                for annex in structured_annexes:
                    self.logger.info(f"Send {annex['title']}")
                    try:
                        response = self.session.post(
                            url,
                            headers={"Content-Type": "application/json"},
                            json=annex
                        )
                        reponses['data'].append(response.json())
                    except Exception as e:
                        self.logger.error(f"fail at {annex['title']} : {e}")
                return reponses
                #     self.logger.info(f"Envoi {annex['title']}")
                #     self.add_job('add_annex', destination=url, annex=annex)
                # return {'msg': 'Transfert planifié', 'err': 0}

    def add_annex(self, destination, annex):
        try:
            response = self.session.post(
                destination,
                headers={"Content-Type": "application/json"},
                json=annex
            )
        except:
            self.logger.error(f"Error to send annex {annex['title']}")
