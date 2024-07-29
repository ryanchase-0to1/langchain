""""""

import datetime
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import requests
from langsmith import Client as LangSmithClient
from urllib3 import Retry

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import RunnableConfig, RunnableSerializable


class LangSmithExampleSelector(
    RunnableSerializable[Union[Dict[str, Any], str], ChatPromptValue]
):
    """Retrieve examples from LangSmith.

    Example:
        .. code-block:: python

            from langchain_core.example_selectors import LangSmithExampleSelector
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.runnables import RunnablePassthrough


            example_selector = LangSmithExampleSelector(dataset_id="...", top_k=5)
            prompt = ChatPromptTemplate([
                    ("system", "..."),
                    ("placeholder", "{examples}"),
                    ("placeholder", "{chat_history}"}),
                    ("human", "i want to know about {foo} in {bar}"),
                ],
            )
            chain = (
                RunnablePassthrough.assign(examples=example_selector)
                | prompt
                | llm
                | ...
            )

    """

    top_k: int
    """Number of examples to retrieve."""
    dataset_id: Optional[Union[str, uuid.UUID]] = None
    """"""
    dataset_name: Optional[str] = None
    """"""
    as_of: Optional[Union[datetime.datetime, str]] = None
    """"""
    limit: Optional[int] = None
    """Max number of examples to search over. 
    
    Oldest examples are dropped if limit is exceeded.
    """
    splits: Optional[Sequence[str]] = None
    """"""
    # TODO: Should we provide nicer interfaces for common filters? E.g. by feedback?
    # Or is user expected to have already done that when they create the dataset.
    filter: Optional[str] = None
    """"""
    client: LangSmithClient
    """LangSmith client."""

    def __init__(
        self,
        *,
        client: Optional[LangSmithClient] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        retry_config: Optional[Retry] = None,
        timeout_ms: Optional[Union[int, Tuple[int, int]]] = None,
        session: Optional[requests.Session] = None,
        **kwargs: Any,
    ) -> None:
        if not client:
            client = LangSmithClient(
                api_url,
                api_key=api_key,
                retry_config=retry_config,
                timeout_ms=timeout_ms,
                session=session,
            )
        super().__init__(client=client, **kwargs)  # type: ignore[call-arg]

    def invoke(
        self, input: Union[Dict[str, Any], str], config: Optional[RunnableConfig] = None
    ) -> ChatPromptValue:
        # TODO: Ideally there would be a search_examples API with similar interface to
        # list_examples plus a query and top_k.
        examples = self.client.search_examples(
            input,
            top_k=self.top_k,
            dataset_id=self.dataset_id,
            dataset_name=self.dataset_name,
            as_of=self.as_of,
            splits=self.splits,
            limit=self.limit,
            filter=self.filter,
        )
        messages = []
        for example in examples:
            # TODO: Need to think about handling non-Messages examples.
            messages.extend(example.inputs["messages"])
            messages.extend(example.outputs["messages"])
        messages = _update_message_names(messages)
        return ChatPromptValue(messages=messages)


class LangSmithCustomExampleSelector(
    RunnableSerializable[Union[Dict[str, Any], str], ChatPromptValue]
):
    """Index examples from LangSmith into a vectorstore and search over them.

    Example:
        .. code-block:: python

            from langchain_core.example_selectors import LangSmithCustomExampleSelector
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.runnables import RunnablePassthrough


            example_selector = LangSmithExampleSelector(dataset_id="...", top_k=5)
            example_selector.index(
                ...
            )
            prompt = ChatPromptTemplate([
                    ("system", "..."),
                    ("placeholder", "{examples}"),
                    ("placeholder", "{chat_history}"}),
                    ("human", "i want to know about {foo} in {bar}"),
                ],
            )
            chain = (
                RunnablePassthrough.assign(examples=example_selector)
                | prompt
                | llm
                | ...
            )

    """

    top_k: int
    """Number of examples to retrieve."""
    dataset_id: Optional[Union[str, uuid.UUID]] = None
    """"""
    dataset_name: Optional[str] = None
    """"""
    as_of: Optional[Union[datetime.datetime, str]] = None
    """"""
    limit: Optional[int] = None
    """Max number of examples to search over. 

    Oldest examples are dropped if limit is exceeded.
    """
    splits: Optional[Sequence[str]] = None
    """"""
    # TODO: Should we provide nicer interfaces for common filters? E.g. by feedback?
    # Or is user expected to have already done that when they create the dataset.
    filter: Optional[str] = None
    """"""
    client: LangSmithClient
    """LangSmith client."""

    def __init__(
            self,
            *,
            client: Optional[LangSmithClient] = None,
            api_url: Optional[str] = None,
            api_key: Optional[str] = None,
            retry_config: Optional[Retry] = None,
            timeout_ms: Optional[Union[int, Tuple[int, int]]] = None,
            session: Optional[requests.Session] = None,
            **kwargs: Any,
    ) -> None:
        if not client:
            client = LangSmithClient(
                api_url,
                api_key=api_key,
                retry_config=retry_config,
                timeout_ms=timeout_ms,
                session=session,
            )
        super().__init__(client=client, **kwargs)  # type: ignore[call-arg]

    def invoke(
            self, input: Union[Dict[str, Any], str],
            config: Optional[RunnableConfig] = None
    ) -> ChatPromptValue:
        # TODO: Ideally there would be a search_examples API with similar interface to
        # list_examples plus a query and top_k.
        examples = self.client.search_examples(
            input,
            top_k=self.top_k,
            dataset_id=self.dataset_id,
            dataset_name=self.dataset_name,
            as_of=self.as_of,
            splits=self.splits,
            limit=self.limit,
            filter=self.filter,
        )
        messages = []
        for example in examples:
            # TODO: Need to think about handling non-Messages examples.
            messages.extend(example.inputs["messages"])
            messages.extend(example.outputs["messages"])
        messages = _update_message_names(messages)
        return ChatPromptValue(messages=messages)


def _update_message_names(messages: List[BaseMessage]) -> List[BaseMessage]:
    for msg in messages:
        if not msg.name:
            msg.name = (
                "example_user" if isinstance(msg, HumanMessage) else "example_assistant"
            )
    return messages
