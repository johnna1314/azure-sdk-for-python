# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
FILE: sample_analyze_addon_key_value_pairs.py

DESCRIPTION:
    This sample demonstrates how to detect key-value pairs from the document using the
    add-on 'KEY_VALUE_PAIRS' capability.

    This sample uses Layout model to demonstrate.

    Add-on capabilities accept a list of strings containing values from the `DocumentAnalysisFeature `
    enum class. For more information, see:
    https://aka.ms/azsdk/python/documentintelligence/analysisfeature.

    The following capabilities are free:
    - BARCODES
    - LANGUAGES

    The following capabilities will incur additional charges:
    - FORMULAS
    - OCR_HIGH_RESOLUTION
    - STYLE_FONT
    - QUERY_FIELDS

    See pricing: https://azure.microsoft.com/pricing/details/ai-document-intelligence/.

USAGE:
    python sample_analyze_addon_key_value_pairs.py

    Set the environment variables with your own values before running the sample:
    1) DOCUMENTINTELLIGENCE_ENDPOINT - the endpoint to your Document Intelligence resource.
    2) DOCUMENTINTELLIGENCE_API_KEY - your Document Intelligence API key.
"""

import os


def analyze_key_value_pairs():
    path_to_sample_documents = os.path.abspath(
        os.path.join(
            os.path.abspath(__file__),
            "..",
            "sample_forms/add_ons/fonts_and_languages.png",
        )
    )
    # [START analyze_key_value_pairs]
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import DocumentAnalysisFeature

    endpoint = os.environ["DOCUMENTINTELLIGENCE_ENDPOINT"]
    key = os.environ["DOCUMENTINTELLIGENCE_API_KEY"]

    document_intelligence_client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    # Specify which add-on capabilities to enable.
    with open(path_to_sample_documents, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
            content_type="application/octet-stream",
        )
    result = poller.result()

    print("----Key-value Pair detected in the document----")
    print(f"Detected {len(result.key_value_pairs)} Key-value Pairs:")
    for kvp_idx, kvp in enumerate(result.key_value_pairs):
        print(f"- Key-value Pair #{kvp_idx}: ")
        print(f"    Key '{kvp.key.content}'")
        for region in kvp.key.bounding_regions:
            print(f"        page number {region.page_number}, region: {region.polygon}")
        if kvp.value:
            print(f"    Value: {kvp.value.content}")
            for region in kvp.value.bounding_regions:
                print(f"        page number {region.page_number}, region: {region.polygon}")
        print(f"    Confidence: {kvp.confidence}")

    print("----------------------------------------")
    # [END analyze_key_value_pairs]


if __name__ == "__main__":
    from azure.core.exceptions import HttpResponseError
    from dotenv import find_dotenv, load_dotenv

    try:
        load_dotenv(find_dotenv())
        analyze_key_value_pairs()
    except HttpResponseError as error:
        # Examples of how to check an HttpResponseError
        # Check by error code:
        if error.error is not None:
            if error.error.code == "InvalidImage":
                print(f"Received an invalid image error: {error.error}")
            if error.error.code == "InvalidRequest":
                print(f"Received an invalid request error: {error.error}")
            # Raise the error again after printing it
            raise
        # If the inner error is None and then it is possible to check the message to get more information:
        if "Invalid request".casefold() in error.message.casefold():
            print(f"Uh-oh! Seems there was an invalid request: {error}")
        # Raise the error again
        raise
