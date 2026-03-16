(ns lanterna-magica.routes
  (:require
   [lanterna-magica.events :as-alias events]
   [re-frame.core :as rf]
   [reitit.frontend :as rtf]
   [reitit.frontend.controllers :as rfc]
   [reitit.frontend.easy :as rtfe]))

(def routes
  [["/"              {:name :route/home}]
   ["/dimensions"    {:name :route/dimensions}]
   ["/shared-values"
    [""    {:name        :route/shared-values
            :controllers [{:start (fn [_] (rf/dispatch [::events/fetch-shared-values]))}]}]
    ["/:id" {:name        :route/shared-value
             :controllers [{:parameters {:path [:id]}
                            :start      (fn [params]
                                          (rf/dispatch [::events/fetch-shared-values])
                                          (rf/dispatch [::events/load-shared-value
                                                        (get-in params [:path :id])]))
                            :stop       (fn [_]
                                          (rf/dispatch [::events/deselect-shared-value]))}]}]]
   ["/configurations"
    [""    {:name        :route/configurations
            :controllers [{:start (fn [_] (rf/dispatch [::events/fetch-configurations]))}]}]
    ["/:id" {:name        :route/configuration
             :controllers [{:parameters {:path [:id]}
                            :start      (fn [params]
                                          (rf/dispatch [::events/fetch-configurations])
                                          (rf/dispatch [::events/load-configuration
                                                        (get-in params [:path :id])]))
                            :stop       (fn [_]
                                          (rf/dispatch [::events/deselect-configuration]))}]}]]
   ["/outputs"
    [""    {:name        :route/outputs
            :controllers [{:start (fn [_] (rf/dispatch [::events/fetch-outputs]))}]}]
    ["/:id" {:name        :route/output
             :controllers [{:parameters {:path [:id]}
                            :start      (fn [params]
                                          (rf/dispatch [::events/fetch-outputs])
                                          (rf/dispatch [::events/load-output
                                                        (get-in params [:path :id])]))
                            :stop       (fn [_]
                                          (rf/dispatch [::events/deselect-output]))}]}]]])

(defonce ^:private controllers (atom []))

(defn on-navigate [match _history]
  (when match
    (let [new-controllers (rfc/apply-controllers @controllers match)]
      (reset! controllers new-controllers))
    (rf/dispatch [::navigated match])))

(defn start! []
  (rtfe/start!
    (rtf/router routes)
    on-navigate
    {:use-fragment false}))

(def ^:private route->fetch-event
  {:route/dimensions [::events/fetch-dimension-types]})

(rf/reg-event-fx
  ::navigated
  (fn [{:keys [db]} [_ match]]
    (let [route-name (get-in match [:data :name])
          effects    {:db (assoc db :current-route match)}]
      (if-let [event (route->fetch-event route-name)]
        (assoc effects :dispatch event)
        effects))))

(defn navigate!
  ([route-name]
   (rtfe/push-state route-name))
  ([route-name path-params]
   (rtfe/push-state route-name path-params)))

(defn href
  ([route-name]
   (rtfe/href route-name))
  ([route-name path-params]
   (rtfe/href route-name path-params)))
