(ns lanterna-magica.routes
  (:require [re-frame.core :as rf]
            [reitit.frontend :as rtf]
            [reitit.frontend.easy :as rtfe]))

(def routes
  [["/"               {:name :route/home}]
   ["/services"       {:name :route/services}]
   ["/environments"   {:name :route/environments}]
   ["/shared-values"  {:name :route/shared-values}]
   ["/configurations" {:name :route/configurations}]])

(defn on-navigate [match _history]
  (when match
    (rf/dispatch [::navigated match])))

(defn start! []
  (rtfe/start!
   (rtf/router routes)
   on-navigate
   {:use-fragment false}))

(rf/reg-event-db
 ::navigated
 (fn [db [_ match]]
   (assoc db :current-route match)))

(defn navigate! [route-name]
  (rtfe/navigate route-name))

(defn href [route-name]
  (rtfe/href route-name))
