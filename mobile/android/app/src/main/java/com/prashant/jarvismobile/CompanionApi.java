package com.prashant.jarvismobile;

import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Header;

public interface CompanionApi {
    @GET("api/health")
    Call<ResponseBody> health(@Header("X-Jarvis-Token") String token);
}
