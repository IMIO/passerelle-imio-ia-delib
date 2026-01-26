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
from requests import RequestException


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
        methods=["get"],
        name="test",
        perm="can_access",
        description="Valider la connexion entre iA.Delib et Publik",
        long_description="Cette méthode permet de vérifier si les données de connexion renseignées pour accéder aux "
        "Web Services sont correctes et d’obtenir des informations sur les versions installées.",
        display_order=0,
        display_category="Test",
    )
    def test(self, request):
        url = f"{self.url}@infos"  # Url et endpoint à contacter
        return self.session.get(url).json()

    @endpoint(
        methods=["get"],
        name="read-item",
        description="Récupérer un point",
        long_description="Renvoie un point iA.Délib via son UID iA.Delib",
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
        display_category="Récupération de point",
    )
    def read_item(self, request, uid, config_id, **kwargs):
        url = f"{self.url}@item"  # Url et endpoint à contacter
        params = {
            "UID": uid,
            "config_id": config_id,
        }  # UID de mon point à récupérer et configuration de l'instance iA.Delib.

        # Optionnal parameters
        if kwargs:
            params.update(kwargs)
        try:
            response = self.session.get(url, params=params)
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e}")
            raise APIError(f"iA.Delib Connector Error: {e}")

        json_response = None
        try:
            json_response = response.json()
        except ValueError:
            self.logger.warning("iA.Delib Connector Error: bad JSON response")
            raise APIError("iA.Delib Connector Error: bad JSON response")

        try:
            response.raise_for_status()
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e} {json_response}")
            raise APIError(f"iA.Delib Connector Error: {e} {json_response}")
        return json_response

    @endpoint(
        methods=["get"],
        name="check-status-items",
        description="Vérification qu'un point et ses liaisons sont en statut final",
        long_description="Renvoie True si un point et ses statuts liés sont dans un statut final",
        parameters={
            "uid": {
                "description": "Identifiant d'un Point",
                "example_value": "bce166cfb27946b58aff9ecfa27367fc",
            },
            "config_id": {
                "description": "Identifiant de la config de l'instance iA.Delib",
                "example_value": "meeting-config-college",
            },
            "linked_mode": {
                "description": "mode de liaison utilisée entre les points",
                "example_value": "auto",
            }
        },
        perm="can_access",
        display_category="Récupération de point",
    )
    def check_status_items(self, request, uid, config_id, linked_mode="auto"):
        FINAL_STATUS = ["accepted", "accepted_with_modification", "refused"]
        result = self.read_item(request, uid, config_id, extra_include="linked_items", extra_include_linked_items_mode=linked_mode)
        if result.get("review_state") not in FINAL_STATUS:
            return False
        elif result.get("extra_include_linked_items"):
            for extra_include_linked_item in result.get("extra_include_linked_items"):
                if extra_include_linked_item.get("review_state") not in FINAL_STATUS:
                    return False
        return True

    @endpoint(
        methods=["get"],
        name="read-item-ts-id",
        description="Récupérer un point avec un identifiant externe",
        long_description="Renvoie un point iA.Délib en utilisant un identifiant externe",
        parameters={
            "external_id": {
                "description": "Identifiant TS d'un Point",
                "example_value": "12-350",
            },
            "config_id": {
                "description": "Identifiant de la config de l'instance iA.Delib",
                "example_value": "meeting-config-college",
            },
        },
        perm="can_access",
        display_category="Récupération de point",
    )
    def read_item_ts_id(self, request, external_id, config_id):
        url = f"{self.url}@search"  # Url et endpoint à contacter
        params = {
            "externalIdentifier": external_id,
            "config_id": config_id,
        }
        try:
            response = self.session.get(url, params=params)
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e}")
            raise APIError(f"iA.Delib Connector Error: {e}")

        json_response = None
        try:
            json_response = response.json()
        except ValueError:
            self.logger.warning("iA.Delib Connector Error: bad JSON response")
            raise APIError("iA.Delib Connector Error: bad JSON response")

        try:
            response.raise_for_status()
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e} {json_response}")
            raise APIError(f"iA.Delib Connector Error: {e} {json_response}")
        return json_response

    @endpoint(
        methods=["get"],
        name="search-items",
        description="Faire une recherche dans iA.Delib",
        long_description="Prend un dictionnaire et renvoie une liste de points ou de séances "
        "https://docs.imio.be/iadelib/webservices/acces_rest.html#search-get",
        perm="can_access",
        display_category="Récupération de point",
    )
    def search_items(self, request, **kwargs):
        url = f"{self.url}@search"  # Url et endpoint à contacter
        params = kwargs
        try:
            response = self.session.get(url, params=params)
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e}")
            raise APIError(f"iA.Delib Connector Error: {e}")

        json_response = None
        try:
            json_response = response.json()
        except ValueError:
            self.logger.warning("iA.Delib Connector Error: bad JSON response")
            raise APIError("iA.Delib Connector Error: bad JSON response")

        try:
            response.raise_for_status()
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e} {json_response}")
            raise APIError(f"iA.Delib Connector Error: {e} {json_response}")
        return json_response

    def list_simple_files(self, fields, files):
        result = []
        for file in files:
            if fields.get(file):
                result.append(fields[file])
        return result

    def list_files_of_blocs(self, fields, blocs_of_files):
        result = []
        for bloc_of_files in blocs_of_files:
            if fields.get(bloc_of_files):
                for file in fields[f"{bloc_of_files}_raw"]:
                    result.append(file["fichier"])
        return result

    def structure_annexes(self, files):
        result = []
        for file in files:
            structured_file = {
                "@type": "annex",
                "title": file["filename"],
                "content_category": "annexe",
                "file": {"data": file["content"], "filename": file["filename"]},
            }
            result.append(structured_file)
        return result

    def get_annexes(self, post_data, demand):
        fields = demand.json()["fields"]
        annexes = []
        if "simple_files" in post_data.keys():
            annexes.extend(self.list_simple_files(fields, post_data["simple_files"]))
        if "workflow_files" in post_data.keys():
            annexes.extend(
                self.list_simple_files(
                    demand.json()["workflow"]["fields"], post_data["workflow_files"]
                )
            )
        if "blocs_of_files" in post_data.keys():
            annexes.extend(
                self.list_files_of_blocs(fields, post_data["blocs_of_files"])
            )
        return annexes

    def get_all_files(self, demand, key="content_is_base64", results=None):
        """
        Parcourt la demande et renvoie tous les fichiers présents dans le dictionnaire
        """
        if results is None:
            results = []

        if isinstance(demand, dict):
            if key in demand:
                results.append(demand)
            for value in demand.values():
                self.get_all_files(value, key, results)

        elif isinstance(demand, list):
            for item in demand:
                self.get_all_files(item, key, results)

        return results

    @staticmethod
    def remove_duplicates_files(files):
        seen_values = set()
        unique_files = []

        for file in files:
            if "content" in file:
                content_value = file["content"]
                if content_value not in seen_values:
                    seen_values.add(content_value)
                    unique_files.append(file)
            else:
                unique_files.append(file)  # Garde les éléments sans "content"

        return unique_files

    @endpoint(
        methods=["post"],
        name="create-item",
        description="Créer un point dans iA.Délib",
        long_description="Création d'un point dans iA.Délib à partir des infos du formulaire. Body nécessaire:"
        "api_url, config_id, proposingGroup, category, title, type. Body optionnel: motivation,"
        "decision, simple_files, blocs_of_files, workflow_files, externalIdentifier",
        perm="can_access",
        display_category="Création de point",
    )
    def create_item(self, request, send_files=True):
        files_keys = self.files_keys
        url = f"{self.url}@item"  # Url et endpoint à contacter
        post_data = json.loads(request.body)

        # Get Files
        demand = (
            requests.get(
                post_data["api_url"],
                auth=(self.username, self.password),
                headers={"Accept": "application/json"},
            )
            if send_files
            else None
        )
        annexes = []
        # Only files in key files_keys
        if send_files and len([x for x in post_data.keys() if x in files_keys and post_data.get(x)]) > 0:
            annexes = self.get_annexes(post_data, demand)
        # All Files
        elif send_files:
            annexes = self.get_all_files(demand.json(), key="content_is_base64")
            if len(annexes) > 0:
                annexes = self.remove_duplicates_files(annexes)
        if len(annexes) > 0:
            post_data["__children__"] = self.structure_annexes(annexes)
        try:
            response = self.session.post(
                url,
                headers={"Content-Type": "application/json"},
                json=post_data,
            )
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e}")
            raise APIError(f"iA.Delib Connector Error: {e}")

        json_response = None
        try:
            json_response = response.json()
        except ValueError:
            self.logger.warning("iA.Delib Connector Error: bad JSON response")
            raise APIError("iA.Delib Connector Error: bad JSON response")

        try:
            response.raise_for_status()
        except RequestException as e:
            self.logger.warning(f"iA.Delib Connector Error: {e} {json_response}")
            raise APIError(f"iA.Delib Connector Error: {e} {json_response}")
        return json_response

    @endpoint(
        methods=["post"],
        name="add-annexes",
        description="POST @annex sur un item iA.Delib",
        long_description="Ajout de pièces jointes sur un élément existant de iA.Délib via son UID. Body nécessaire:"
        "api_url, UID. Body optionnel: simple_files, blocs_of_files, workflow_files",
        perm="can_access",
        display_category="Création de point",
    )
    def add_annexes(self, request):
        files_keys = self.files_keys
        post_data = json.loads(request.body)
        url = f"{self.url}@annex/{post_data['UID']}"  # Url et endpoint à contacter
        # Demande concernée
        demand = requests.get(
            post_data["api_url"],
            auth=(self.username, self.password),
            headers={"Accept": "application/json"},
        )

        if len([x for x in post_data.keys() if x in files_keys and post_data.get(x)]) > 0:
            annexes = self.get_annexes(post_data, demand)
        else:
            annexes = self.get_all_files(demand.json(), key="content_is_base64")
            if len(annexes) > 0:
                annexes = self.remove_duplicates_files(annexes)
        if len(annexes) > 0:
            structured_annexes = self.structure_annexes(annexes)
            titles = " ".join([annex["title"] for annex in structured_annexes])
            self.logger.info(f"Début de l'envoi des documents {titles}")
            reponses = {"data": []}
            for annex in structured_annexes:
                self.logger.info(f"Send {annex['title']}")
                try:
                    response = self.session.post(
                        url,
                        headers={"Content-Type": "application/json"},
                        json=annex,
                    )
                    reponses["data"].append(response.json())
                except Exception as e:
                    self.logger.error(f"fail at {annex['title']} : {e}")
            return reponses
            #     self.logger.info(f"Envoi {annex['title']}")
            #     self.add_job('add_annex', destination=url, annex=annex)
            # return {'msg': 'Transfert planifié', 'err': 0}

    def add_annex(self, destination, annex):
        try:
            response = self.session.post(
                destination, headers={"Content-Type": "application/json"}, json=annex
            )
        except:
            self.logger.error(f"Error to send annex {annex['title']}")
