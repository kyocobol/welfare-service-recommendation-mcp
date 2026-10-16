class WelfareApiError(Exception):
    def __init__(
        self,
        api_name: str,
        *,
        status_code: int | None = None,
        result_code: str | None = None,
    ) -> None:
        super().__init__(api_name)
        self.api_name = api_name
        self.status_code = status_code
        self.result_code = result_code


class WelfareApiTimeout(WelfareApiError):
    pass


class WelfareApiRateLimited(WelfareApiError):
    pass


class WelfareApiInvalidParameter(WelfareApiError):
    pass
